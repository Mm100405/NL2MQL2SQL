## 启动说明

### 后端启动
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

### 前端启动
```bash
cd frontend
npm install
npm run dev
```

### 访问地址
- 前端: http://localhost:5173
- 后端API文档: http://localhost:8010/docs
