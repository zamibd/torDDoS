package handlers

import (
	"os/exec"

	"github.com/gofiber/fiber/v3"
)

// Health godoc
// GET /api/health
func Health(c fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"status":  "ok",
		"service": "torDDoS API",
		"version": "2.0.0",
	})
}

// TorStatus godoc
// GET /api/tor/status
func TorStatus(c fiber.Ctx) error {
	// Check binary exists
	path, err := exec.LookPath("tor")
	installed := err == nil

	// Check systemd service is active
	svcErr := exec.Command("systemctl", "is-active", "--quiet", "tor").Run()
	running := svcErr == nil

	return c.JSON(fiber.Map{
		"installed": installed,
		"running":   running,
		"path":      path,
	})
}
