package handlers

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"time"

	"github.com/gofiber/fiber/v3"
	"github.com/zamibd/torddos-api/state"
)

// StartRequest is the JSON body for POST /api/attack/start.
type StartRequest struct {
	Target   string `json:"target"`
	Attempts int    `json:"attempts"`
	Threads  int    `json:"threads"`
}

var ansiRe = regexp.MustCompile(`\x1b\[[0-9;]*m`)

func stripAnsi(s string) string { return ansiRe.ReplaceAllString(s, "") }

// projectDir resolves the torDDoS root directory (one level above the api/ folder).
func projectDir() string {
	if d := os.Getenv("TORDDOS_DIR"); d != "" {
		if abs, err := filepath.Abs(d); err == nil {
			return abs
		}
		return d
	}
	exe, err := os.Executable()
	if err != nil {
		return ".."
	}
	return filepath.Join(filepath.Dir(exe), "..")
}

// StartAttack godoc
// POST /api/attack/start
func StartAttack(c fiber.Ctx) error {
	if state.Global.IsRunning() {
		return c.Status(fiber.StatusConflict).JSON(fiber.Map{
			"error": "an attack is already running",
		})
	}

	var req StartRequest
	if err := c.Bind().JSON(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid request body: " + err.Error(),
		})
	}
	if req.Target == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "target is required"})
	}
	if req.Attempts <= 0 {
		req.Attempts = 10
	}
	if req.Threads <= 0 {
		req.Threads = 3
	}

	dir := projectDir()
	python := filepath.Join(dir, "venv", "bin", "python3")
	script := filepath.Join(dir, "torddos.py")

	cmd := exec.Command(python, script,
		"-t", req.Target,
		"-n", strconv.Itoa(req.Attempts),
		"--threads", strconv.Itoa(req.Threads),
	)

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return c.Status(500).JSON(fiber.Map{"error": "stdout pipe: " + err.Error()})
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		return c.Status(500).JSON(fiber.Map{"error": "stderr pipe: " + err.Error()})
	}

	if err := cmd.Start(); err != nil {
		return c.Status(500).JSON(fiber.Map{"error": "failed to start: " + err.Error()})
	}

	state.Global.SetCmd(cmd, req.Target, req.Attempts, req.Threads)

	// Stream stdout → log broadcast
	go func() {
		sc := bufio.NewScanner(stdout)
		for sc.Scan() {
			state.Global.AppendLog(stripAnsi(sc.Text()))
		}
	}()

	// Stream stderr → log broadcast
	go func() {
		sc := bufio.NewScanner(stderr)
		for sc.Scan() {
			state.Global.AppendLog("[err] " + stripAnsi(sc.Text()))
		}
	}()

	// Wait for process exit → mark stopped
	go func() {
		cmd.Wait()
		state.Global.SetStopped()
	}()

	return c.Status(fiber.StatusAccepted).JSON(fiber.Map{
		"message":  "attack started",
		"target":   req.Target,
		"attempts": req.Attempts,
		"threads":  req.Threads,
	})
}

// StopAttack godoc
// POST /api/attack/stop
// Idempotent: always returns 200 so the UI can safely reset state.
func StopAttack(c fiber.Ctx) error {
	if !state.Global.IsRunning() {
		// Nothing running — acknowledge gracefully so the client can reset its UI
		return c.JSON(fiber.Map{"message": "no attack running", "already_stopped": true})
	}
	state.Global.Stop()
	return c.JSON(fiber.Map{"message": "attack stopped", "already_stopped": false})
}

// GetStatus godoc
// GET /api/attack/status
func GetStatus(c fiber.Ctx) error {
	return c.JSON(state.Global.Status())
}

// StreamLogs godoc
// GET /api/attack/logs  — Server-Sent Events
func StreamLogs(c fiber.Ctx) error {
	c.Set("Content-Type", "text/event-stream")
	c.Set("Cache-Control", "no-cache")
	c.Set("Connection", "keep-alive")
	c.Set("X-Accel-Buffering", "no")

	userCtx := c.Context()

	// Snapshot existing logs & subscribe before entering the writer
	existing := state.Global.RecentLogs()
	ch := state.Global.Subscribe()

	return c.SendStreamWriter(func(w *bufio.Writer) {
		defer state.Global.Unsubscribe(ch)

		// Replay buffered logs to the new client
		for _, line := range existing {
			fmt.Fprintf(w, "data: %s\n\n", line)
		}
		_ = w.Flush()

		ticker := time.NewTicker(20 * time.Second)
		defer ticker.Stop()

		for {
			select {
			case <-userCtx.Done():
				// Client disconnected
				return

			case msg, ok := <-ch:
				if !ok {
					// Attack finished — send done event and close
					fmt.Fprintf(w, "event: done\ndata: attack finished\n\n")
					_ = w.Flush()
					return
				}
				fmt.Fprintf(w, "data: %s\n\n", msg)
				_ = w.Flush()

			case <-ticker.C:
				// Heartbeat to keep the connection alive through proxies
				fmt.Fprintf(w, ": ping\n\n")
				_ = w.Flush()
			}
		}
	})
}
