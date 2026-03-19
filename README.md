# SBL Designer — Guía de Despliegue en Azure

## Estructura del Proyecto
```
sbl-app/
├── app.py              # Flask backend + Anthropic API
├── templates/
│   └── index.html      # Frontend (single page, 3 fases)
├── requirements.txt
└── README.md
```

## Despliegue Rápido en Azure Ubuntu VM

### 1. Subir archivos al servidor
```bash
# Desde tu máquina local
scp -r sbl-app/ azureuser@<TU-IP>:~/sbl-app/
```

### 2. Instalar dependencias
```bash
cd ~/sbl-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configurar API Key
```bash
# Opción A: Variable de entorno
export ANTHROPIC_API_KEY="sk-ant-..."

# Opción B: Archivo .env (crear)
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env
echo 'FLASK_SECRET=tu-secret-key-aqui' >> .env
```

### 4. Test local
```bash
source venv/bin/activate
export ANTHROPIC_API_KEY="sk-ant-..."
python app.py
# Visita http://localhost:5000
```

### 5. Producción con Gunicorn
```bash
# Crear servicio systemd
sudo tee /etc/systemd/system/sbl-app.service << 'EOF'
[Unit]
Description=SBL Designer Flask App
After=network.target

[Service]
User=azureuser
WorkingDirectory=/home/azureuser/sbl-app
Environment="ANTHROPIC_API_KEY=sk-ant-..."
Environment="FLASK_SECRET=tu-secret-key"
ExecStart=/home/azureuser/sbl-app/venv/bin/gunicorn --bind 127.0.0.1:5001 --workers 4 --timeout 120 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable sbl-app
sudo systemctl start sbl-app
```

### 6. Nginx (si ya tienes Nginx configurado)
```nginx
# Agregar a tu configuración de Nginx
server {
    listen 80;
    server_name sbl.tu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
        proxy_connect_timeout 120s;
    }
}
```

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 7. SSL con Certbot
```bash
sudo certbot --nginx -d sbl.tu-dominio.com
```

## Notas Importantes

- **Timeout**: Las llamadas a la API de Anthropic pueden tomar 15-30 segundos. Gunicorn y Nginx están configurados con timeout de 120s.
- **Rate Limiting**: Con 20-30 estudiantes simultáneos, cada uno haciendo ~5-10 API calls por sesión, necesitas ~150-300 calls totales. La API de Anthropic maneja esto sin problema.
- **Costo estimado**: ~$0.50-1.00 por sesión completa del workshop (Sonnet 4).
- **Sin base de datos**: La app usa session storage de Flask. Los escenarios viven en la sesión del navegador.

## Endpoints de la API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Frontend principal |
| GET | `/api/health` | Status de la API |
| POST | `/api/generate` | Fase 1: Generar escenario |
| POST | `/api/refine` | Fase 2: Refinar escenario |
| POST | `/api/play` | Fase 3: Jugar decisión |
