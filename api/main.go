package main

import (
	"log"
	"os"
	"strings"

	"github.com/gofiber/fiber/v3"
	"github.com/gofiber/fiber/v3/extractors"
	"github.com/gofiber/fiber/v3/middleware/cors"
	"github.com/gofiber/fiber/v3/middleware/keyauth"
	"github.com/gofiber/fiber/v3/middleware/logger"
	"github.com/gofiber/fiber/v3/middleware/recover"
	"github.com/gofiber/fiber/v3/middleware/static"
	"github.com/zamibd/torddos-api/handlers"
)

func main() {
	app := fiber.New(fiber.Config{
		AppName:       "torDDoS API v2.0",
		StrictRouting: false,
		CaseSensitive: false,
	})

	// ── Global middleware ──────────────────────────────────────────────────────
	app.Use(recover.New())
	app.Use(logger.New(logger.Config{
		Format: "[${time}] ${status} ${latency} ${method} ${path}\n",
	}))

	allowedOrigins := os.Getenv("ALLOWED_ORIGINS")
	originsList := []string{"*"}
	if allowedOrigins != "" {
		originsList = strings.Split(allowedOrigins, ",")
	}

	app.Use(cors.New(cors.Config{
		AllowOrigins: originsList,
		AllowMethods: []string{"GET", "POST", "DELETE", "OPTIONS"},
		AllowHeaders: []string{"Origin", "Content-Type", "Accept", "Authorization", "X-API-Key"},
	}))

	// ── Routes ─────────────────────────────────────────────────────────────────
	// Serve frontend dashboard
	app.Get("/*", static.New("./public"))

	api := app.Group("/api")

	// Health (Unauthenticated)
	api.Get("/health", handlers.Health)

	// Authentication Middleware for sensitive routes
	apiKey := os.Getenv("API_KEY")
	if apiKey != "" {
		api.Use(keyauth.New(keyauth.Config{
			Extractor: extractors.FromHeader("X-API-Key"),
			Validator: func(c fiber.Ctx, key string) (bool, error) {
				return key == apiKey, nil
			},
		}))
	}

	// Tor service info
	api.Get("/tor/status", handlers.TorStatus)

	// Attack lifecycle
	attack := api.Group("/attack")
	attack.Post("/start", handlers.StartAttack)
	attack.Post("/stop", handlers.StopAttack)
	attack.Get("/status", handlers.GetStatus)
	attack.Get("/logs", handlers.StreamLogs) // SSE

	// ── Start server ───────────────────────────────────────────────────────────
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("torDDoS API listening on :%s", port)
	if err := app.Listen(":" + port); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
