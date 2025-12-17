# README

pip install -r requirements.txt

# Run the server 

uvicorn app:app --host 0.0.0.0 --port 8000 --reload

uvicorn app:app --host 0.0.0.0 --port 8000


notes - 

app:app means “import app from app.py”

0.0.0.0 exposes the server in Codespaces

--reload restarts on file changes

`--host 0.0.0.0` is req in codespaces 


# Testing 

curl -X POST "http://127.0.0.1:8000/card/100/payment" \
  -H "Content-Type: application/json" \
  -d '{"amount": 7500}'

# format response:

curl -s -X POST http://127.0.0.1:8000/card/100/payment \
  -H "Content-Type: application/json" \
  -d '{"amount": 7500}' | python -m json.tool



# Reset - 

curl -X POST https://torch-handson-5403bd9ca59f.herokuapp.com/reset \
  -H "X-Torch-Auth: teeth" \
  -H "Content-Type: application/json" \
  -d '{}'


# Test idempotency key

curl -X POST http://127.0.0.1:8000/card/100/payment \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: card100-7500" \
  -d '{"amount": 7500}' | python -m json.tool

---
# set up - 

export BASE="http://127.0.0.1:8000"
export TORCH="https://torch-handson-5403bd9ca59f.herokuapp.com"



# Open this in browser 
https://<your-codespace>-8000.app.github.dev/docs

https://obscure-bassoon-j4jvp767wgp2pvgx-8000.app.github.dev/docs 
