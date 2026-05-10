package state

import (
	"os/exec"
	"sync"
	"time"
)

// AttackStatus is the JSON shape returned by GET /api/attack/status.
type AttackStatus struct {
	Running   bool      `json:"running"`
	Target    string    `json:"target"`
	Attempts  int       `json:"attempts"`
	Threads   int       `json:"threads"`
	StartedAt time.Time `json:"started_at,omitempty"`
	RecentLogs []string `json:"recent_logs"`
}

// Manager holds the global attack state and SSE subscriber list.
type Manager struct {
	mu        sync.RWMutex
	running   bool
	cmd       *exec.Cmd
	logs      []string
	target    string
	attempts  int
	threads   int
	startedAt time.Time

	subsMu sync.Mutex
	subs   []chan string
}

const maxLogs = 200

// Global is the singleton state manager used by all handlers.
var Global = &Manager{}

// ── Getters ───────────────────────────────────────────────────────────────────

func (m *Manager) IsRunning() bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.running
}

func (m *Manager) RecentLogs() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	cp := make([]string, len(m.logs))
	copy(cp, m.logs)
	return cp
}

func (m *Manager) Status() AttackStatus {
	m.mu.RLock()
	defer m.mu.RUnlock()
	logs := make([]string, len(m.logs))
	copy(logs, m.logs)
	return AttackStatus{
		Running:    m.running,
		Target:     m.target,
		Attempts:   m.attempts,
		Threads:    m.threads,
		StartedAt:  m.startedAt,
		RecentLogs: logs,
	}
}

// ── Setters ───────────────────────────────────────────────────────────────────

func (m *Manager) SetCmd(cmd *exec.Cmd, target string, attempts, threads int) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.cmd = cmd
	m.running = true
	m.target = target
	m.attempts = attempts
	m.threads = threads
	m.startedAt = time.Now()
	m.logs = []string{}
}

// Stop kills the running process immediately.
func (m *Manager) Stop() {
	m.mu.Lock()
	if m.cmd != nil && m.cmd.Process != nil {
		m.cmd.Process.Kill()
	}
	m.running = false
	m.cmd = nil
	m.mu.Unlock()
	m.closeAllSubs()
}

// SetStopped is called by the goroutine that waits for cmd.Wait().
func (m *Manager) SetStopped() {
	m.mu.Lock()
	m.running = false
	m.cmd = nil
	m.mu.Unlock()
	m.closeAllSubs()
}

// ── Logging & SSE broadcast ───────────────────────────────────────────────────

func (m *Manager) AppendLog(line string) {
	m.mu.Lock()
	m.logs = append(m.logs, line)
	if len(m.logs) > maxLogs {
		m.logs = m.logs[len(m.logs)-maxLogs:]
	}
	m.mu.Unlock()
	m.broadcast(line)
}

func (m *Manager) broadcast(msg string) {
	m.subsMu.Lock()
	defer m.subsMu.Unlock()
	for _, ch := range m.subs {
		select {
		case ch <- msg:
		default: // drop if subscriber is slow
		}
	}
}

func (m *Manager) Subscribe() chan string {
	ch := make(chan string, 64)
	m.subsMu.Lock()
	m.subs = append(m.subs, ch)
	m.subsMu.Unlock()
	return ch
}

func (m *Manager) Unsubscribe(ch chan string) {
	m.subsMu.Lock()
	defer m.subsMu.Unlock()
	for i, sub := range m.subs {
		if sub == ch {
			m.subs = append(m.subs[:i], m.subs[i+1:]...)
			close(ch)
			return
		}
	}
}

func (m *Manager) closeAllSubs() {
	m.subsMu.Lock()
	defer m.subsMu.Unlock()
	for _, ch := range m.subs {
		close(ch)
	}
	m.subs = nil
}
