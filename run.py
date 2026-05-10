from mp_expenses_audit.pipeline import run_pipeline


if __name__ == "__main__":
	output_paths = run_pipeline()
	for name, path in output_paths.items():
		print(f"{name}: {path}")
