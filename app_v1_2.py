from pathlib import Path

restore_file = Path(__file__).with_name("app_v1_2_RESTORE.py")
exec(
    compile(
        restore_file.read_text(encoding="utf-8"),
        str(restore_file),
        "exec",
    ),
    globals(),
    globals(),
)
