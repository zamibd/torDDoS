.PHONY: dev build run tidy

# Resolve the torDDoS project root (parent of api/)
TORDDOS_DIR ?= $(shell cd .. && pwd)

tidy:
	go mod tidy

build: tidy
	go build -o bin/torddos-api ./...

dev: tidy
	TORDDOS_DIR=$(TORDDOS_DIR) PORT=8080 go run ./...

run: build
	TORDDOS_DIR=$(TORDDOS_DIR) PORT=8080 ./bin/torddos-api
