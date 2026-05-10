from mp_expenses_audit.pipeline import run_pipeline


def main() -> None:
    output_paths = run_pipeline()
    for name, path in output_paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()