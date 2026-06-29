# Repository layout (PDF mapping)

```
projects/piter-aiops/
├── app/                    # Flask backend (PDF: backend/app/)
├── action_groups/          # Bedrock Lambdas (PDF: lambdas/)
├── frontend/               # Vite React SPA source
├── app/static/spa/         # Built SPA assets (production)
├── data/source/            # Canonical operational datasets
├── knowledge_base/         # KB corpus (JSON local + MD for S3 sync)
├── infra/                  # AWS setup, agent instructions
├── tests/                  # pytest suite
├── screenshots/final/      # Submission screenshots (PDF: presentation/)
└── presentation/           # Pointer README → screenshots/final/
```
