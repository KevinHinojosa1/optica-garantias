#!/bin/bash
# Crear repo en GitHub y dejar listo para Render
set -e
cd "$(dirname "$0")/.."

REPO_NAME="${1:-optica-garantias}"

echo "========================================="
echo "  Despliegue — GitHub + Render"
echo "========================================="
echo ""

if ! command -v gh &>/dev/null; then
  echo "Instalando GitHub CLI..."
  brew install gh
fi

if ! gh auth status &>/dev/null; then
  echo "⚠️  No estás logueado en GitHub."
  echo "    Ejecuta primero:  gh auth login"
  echo "    (elige GitHub.com → HTTPS → Login with a web browser)"
  exit 1
fi

USER=$(gh api user -q .login)
echo "✅ GitHub: $USER"
echo ""

if git remote get-url origin &>/dev/null; then
  echo "Remote origin ya existe. Haciendo push..."
  git push -u origin main
else
  echo "Creando repositorio público: $REPO_NAME"
  gh repo create "$REPO_NAME" \
    --public \
    --source=. \
    --remote=origin \
    --description "Sistema de gestión de garantías — Óptica Los Andes" \
    --push
fi

REPO_URL="https://github.com/$USER/$REPO_NAME"
echo ""
echo "========================================="
echo "  ✅ GitHub listo"
echo "  $REPO_URL"
echo "========================================="
echo ""
echo "Siguiente paso — Render:"
echo "  1. Abre: https://dashboard.render.com/select-repo?type=blueprint"
echo "  2. Conecta GitHub si te lo pide (Sign in with GitHub)"
echo "  3. Elige el repo: $REPO_NAME"
echo "  4. Render detectará render.yaml automáticamente"
echo "  5. En Environment, agrega:"
echo "       ANTHROPIC_API_KEY = tu clave de Claude"
echo "  6. Clic en Apply / Create"
echo ""
echo "En ~5 min tendrás una URL como:"
echo "  https://$REPO_NAME.onrender.com"
echo ""