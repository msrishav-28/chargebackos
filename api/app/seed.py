from app.services.seed import run_seed

if __name__ == "__main__":
    result = run_seed(reset=False)
    print(result)
