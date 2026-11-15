# Diário de Uso de IA — EventHub

| Data | Objetivo | Prompt Principal | Sugestão da IA | Decisão | Justificativa | Erro/Limitação Identificada e Correção |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 15/11/2026 | Estruturação inicial do `events_service` e segurança de variáveis | Geração da estrutura de pastas, `.gitignore`, `.env.example` e código base do MS Events em Flask | Uso de JWT compartilhado via `.env`, validação RBAC por decorador e token interno (`X-Internal-Token`) para rotas `/internal` | Aceita | Garante isolamento de segredos fora do GitHub e impede acesso não autorizado às rotas administrativas e internas | Nenhuma falha crítica nesta etapa; validado localmente via Swagger (`/apidocs`) |
