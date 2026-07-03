# Makefile
tailwind-build:
    cd static/css && .\tailwindcss.exe -i input.css -o app.css --minify

tailwind-watch:
    cd static/css && .\tailwindcss.exe -i input.css -o app.css --watch