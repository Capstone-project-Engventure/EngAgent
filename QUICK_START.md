# ⚡ Quick Start - Memory Optimization & DeepSeek

## 🚨 Lỗi hiện tại:
```
ValueError: Ollama call failed with status code 500. 
Details: {"error":"model requires more system memory (4.8 GiB) than is available (1.9 GiB)"}
```

## 🚀 Giải pháp nhanh (3 bước):

### 🔧 Bước 1: Setup model nhỏ hơn
```bash
cd run_LLM

# Option A: Auto setup (Khuyến nghị)
python setup_models.py

# Option B: Manual setup
ollama pull llama3.2:1b
echo "OLLAMA_MODEL=llama3.2:1b" >> .env
```

### 🌟 Bước 2: Setup DeepSeek API (Khuyến nghị cao)
```bash
# Auto setup với script
python setup_deepseek.py

# Manual setup:
# 1. Đăng ký tại: https://platform.deepseek.com
# 2. Lấy API key
# 3. Thêm vào .env:
echo "USE_DEEPSEEK=true" >> .env
echo "DEEPSEEK_API_KEY=sk-your-key-here" >> .env
```

### 🧪 Bước 3: Test
```bash
# Start app
python -m uvicorn app.main:app --reload

# Test health
curl http://localhost:8000/health

# Test generation
curl -X POST "http://localhost:8000/api/exercises/no-rag?modelType=deepseek" \
  -H "Content-Type: application/json" \
  -d '{"prompt_name": "english_exercise_default", "number": 2, "type": "mcq", "skill": "vocabulary", "level": "beginner", "topic": "animals"}'
```

## 📊 So sánh giải pháp:

| Giải pháp | Thời gian setup | Cost | Performance | RAM cần |
|-----------|----------------|------|-------------|---------|
| **Model nhỏ (llama3.2:1b)** | 5 phút | Free | Good | ~1.3GB |
| **DeepSeek API** | 10 phút | ~$5/tháng | Excellent | Minimal |
| **Upgrade RAM** | Vài giờ | $50-200 | Excellent | 8GB+ |

## 🎯 Khuyến nghị:

### 💰 **Budget thấp:**
- Sử dụng `llama3.2:1b` cho development
- DeepSeek API cho production

### 🚀 **Production:**
- DeepSeek API làm primary
- Ollama model nhỏ làm backup
- Auto fallback khi quota hết

### ⚡ **Ngay lập tức:**
```bash
# Quick fix để test ngay:
cd run_LLM
python setup_models.py  # Chọn model nhỏ
python -m uvicorn app.main:app --reload
```

## 📚 Chi tiết:
- **Memory optimization:** `MEMORY_OPTIMIZATION_GUIDE.md`
- **DeepSeek setup:** `DEEPSEEK_API_GUIDE.md`
- **Full documentation:** `README.md`

## 🆘 Cần hỗ trợ?
1. Chạy `python setup_models.py` để auto-fix
2. Kiểm tra `curl http://localhost:8000/health`
3. Đọc error logs để troubleshoot
4. Sử dụng DeepSeek API để bypass memory issues

**🎉 Với 2 script trên, bạn sẽ giải quyết được vấn đề memory và có thêm DeepSeek API trong vòng 10 phút!** 