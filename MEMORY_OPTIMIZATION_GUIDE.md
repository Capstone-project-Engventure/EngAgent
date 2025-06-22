# 🧠 Memory Optimization & DeepSeek Integration Guide

## 🚨 Giải quyết lỗi Memory với Ollama

### Lỗi hiện tại:
```
ValueError: Ollama call failed with status code 500. 
Details: {"error":"model requires more system memory (4.8 GiB) than is available (1.9 GiB)"}
```

### 💡 Các giải pháp:

#### 1. **Sử dụng model nhỏ hơn (Khuyến nghị)**

**Trước khi bắt đầu, hãy chạy script setup:**
```bash
cd run_LLM
python setup_models.py
```

**Hoặc cài đặt thủ công:**

```bash
# Model nhỏ (~1.3GB) - phù hợp với RAM 2GB
ollama pull llama3.2:1b

# Model trung bình (~2.0GB) - phù hợp với RAM 3-4GB  
ollama pull llama3.2:3b

# Model lớn (~4.8GB) - cần RAM 6GB+
ollama pull mistral
```

**Cập nhật file `.env`:**
```env
# Chọn model phù hợp với RAM của bạn
OLLAMA_MODEL=llama3.2:1b   # Cho RAM thấp
# OLLAMA_MODEL=llama3.2:3b   # Cho RAM trung bình
# OLLAMA_MODEL=mistral       # Cho RAM cao
```

#### 2. **Tối ưu hóa Ollama**

**Giảm context length:**
```bash
# Tạo Modelfile tùy chỉnh
cat > Modelfile <<EOF
FROM llama3.2:1b
PARAMETER num_ctx 2048
PARAMETER num_predict 512
EOF

# Tạo model tùy chỉnh
ollama create llama3.2-optimized -f Modelfile
```

**Cập nhật `.env`:**
```env
OLLAMA_MODEL=llama3.2-optimized
OLLAMA_TIMEOUT=300
```

#### 3. **Sử dụng DeepSeek API (Khuyến nghị cao)**

DeepSeek cung cấp API mạnh mẽ, không cần RAM local:

**Đăng ký DeepSeek API:**
1. Truy cập: https://platform.deepseek.com
2. Đăng ký tài khoản
3. Lấy API key từ dashboard

**Cấu hình DeepSeek:**
```env
USE_DEEPSEEK=true
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

## 🌟 Cách sử dụng DeepSeek

### 1. **API Call với DeepSeek**

```bash
# Test API với DeepSeek
curl -X POST "http://localhost:8000/api/exercises/no-rag?modelType=deepseek" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_name": "english_exercise_default",
    "number": 5,
    "type": "mcq",
    "skill": "grammar",
    "level": "intermediate",
    "topic": "present perfect"
  }'
```

### 2. **Fallback Strategy**

Hệ thống sẽ tự động fallback khi một model gặp lỗi:

```
DeepSeek (ưu tiên) → Vertex AI → Ollama (local)
```

### 3. **Kiểm tra trạng thái**

```bash
curl http://localhost:8000/health
```

Kết quả sẽ hiển thị trạng thái của tất cả models:
```json
{
  "status": "healthy",
  "components": {
    "ollama_llm": {"ok": true},
    "vertex_llm": {"ok": false},
    "deepseek_llm": {"ok": true},
    "config": {
      "ollama_model": "llama3.2:1b",
      "use_deepseek": true,
      "deepseek_configured": true
    }
  }
}
```

## 🔧 Cài đặt và cấu hình

### 1. **Cài đặt dependencies**

```bash
cd run_LLM
pip install -r requirements.txt
```

### 2. **Chạy setup script**

```bash
python setup_models.py
```

Script này sẽ:
- Kiểm tra RAM hệ thống
- Đề xuất model phù hợp
- Cài đặt Ollama model
- Cấu hình DeepSeek (optional)
- Tạo file `.env`

### 3. **Test hệ thống**

```bash
# Khởi động service
python -m uvicorn app.main:app --reload

# Test health check
curl http://localhost:8000/health

# Test API với model nhỏ
curl -X POST "http://localhost:8000/api/exercises/no-rag?modelType=ollama" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_name": "english_exercise_default",
    "number": 2,
    "type": "mcq", 
    "skill": "vocabulary",
    "level": "beginner",
    "topic": "animals"
  }'
```

## 📊 So sánh Models

| Model | RAM Required | Performance | Cost | Use Case |
|-------|-------------|-------------|------|----------|
| `llama3.2:1b` | ~1.3GB | Good | Free | Development, testing |
| `llama3.2:3b` | ~2.0GB | Better | Free | Small production |
| `mistral` | ~4.8GB | Excellent | Free | High-end local |
| `DeepSeek API` | Minimal | Excellent | Paid | Production recommended |

## 🚀 Khuyến nghị Production

### Setup lai tự động:
```bash
# 1. Setup môi trường
python setup_models.py

# 2. Cấu hình DeepSeek cho production  
echo "USE_DEEPSEEK=true" >> .env
echo "DEEPSEEK_API_KEY=your_key" >> .env

# 3. Backup với Ollama model nhỏ
echo "OLLAMA_MODEL=llama3.2:1b" >> .env

# 4. Test tất cả models
python -c "
import requests
models = ['deepseek', 'ollama']
for model in models:
    try:
        resp = requests.get(f'http://localhost:8000/health')
        print(f'{model}: OK' if resp.status_code == 200 else f'{model}: Error')
    except:
        print(f'{model}: Offline')
"
```

## 🔧 Troubleshooting

### Lỗi Memory vẫn còn:
1. Restart Ollama: `ollama serve`
2. Clear model cache: `ollama rm <model_name>`
3. Sử dụng model nhỏ hơn
4. Chuyển sang DeepSeek API

### DeepSeek API không hoạt động:
1. Kiểm tra API key
2. Verify internet connection  
3. Check API quota/billing

### Performance thấp:
1. Tăng `OLLAMA_TIMEOUT` trong `.env`
2. Sử dụng GPU nếu có
3. Close các ứng dụng khác

## 📞 Support

Nếu vẫn gặp vấn đề:
1. Chạy `python setup_models.py` để re-configure
2. Check logs: `tail -f /var/log/ollama.log`
3. Test từng component riêng lẻ
4. Sử dụng DeepSeek API làm primary solution 