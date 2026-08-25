#!/usr/bin/env bash
set -euo pipefail
mkdir -p assets/product
curl -L --fail --retry 3 --silent --show-error 'https://alamaarhpl.com/wp-content/uploads/2026/07/alamaar-product-1783876221037-exec-87c76e4e-1a79-49cb-8002-c2ef5c523b3e-wpak.webp?wpakv=1785065993' -o assets/product/orchid-hero.webp
curl -L --fail --retry 3 --silent --show-error 'https://alamaarhpl.com/wp-content/uploads/2026/07/alamaar-product-1783876205680-exec-05eba82f-98cd-4ba1-abe6-56cdbeb5321c-wpak.webp?wpakv=1785065994' -o assets/product/orchid-interior.webp
curl -L --fail --retry 3 --silent --show-error 'https://alamaarhpl.com/wp-content/uploads/2026/07/alamaar-product-1783876241626-exec-10ce8701-6c83-4e99-b810-863b438537b7-wpak.webp?wpakv=1785065997' -o assets/product/orchid-panel.webp
curl -L --fail --retry 3 --silent --show-error 'https://alamaarhpl.com/wp-content/uploads/2026/07/orchid-elegance-dg-818-a-208-prplus-finish-wpak.webp?wpakv=1785065994' -o assets/product/orchid-texture.webp
curl -L --fail --retry 3 --silent --show-error 'https://alamaarhpl.com/wp-content/uploads/2026/07/orchid-elegance-dg-818-a-208-prplus-application-1-scaled-wpak.webp?wpakv=1785065993' -o assets/product/orchid-application.webp
for f in assets/product/*.webp; do test -s "$f"; done
