# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 安裝 git（某些 Go 模組需要）
RUN apk add --no-cache git

# 複製 go.mod 和 go.sum
COPY go.mod ./

# 下載依賴
RUN go mod download

# 複製原始碼
COPY . .

# 編譯二進位檔
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main .

# Runtime stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /app

# 從 builder 複製編譯好的二進位檔
COPY --from=builder /app/main .

# 暴露 port
EXPOSE 3001

# 執行
CMD ["./main"]

