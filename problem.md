# Problem

As a computer science student, I've noticed that understanding an unfamiliar codebase can be pretty overwhelming, especially when working on group projects or exploring open-source repositories on GitHub. It's not always obvious where to start, which files contain most of the logic, or how the project is structured. Going through every file manually takes time, and it's easy to miss important details. This can make it harder for students and new developers to understand a project, contribute to it, or make changes confidently.

# Initial requirements

- R1: The program should accept a folder path through the command line and scan all Python files inside that folder, including files in subfolders.
- R2: For each Python file, display its relative path and count the total lines of code, excluding blank lines and comments.
- R3: Count the functions and classes in each file, including asynchronous functions.
- R4: Display a summary at the end showing the total number of Python files scanned, lines of code, functions, and classes.
- R5: Automatically skip unnecessary directories such as .git, .venv, venv, and __pycache__.
- R6: Display a clear error message if the provided folder does not exist or cannot be accessed.

# Round 2 requirements

- R7: When RepoLens can't access a folder, show a clear warning with the folder's path, then continue scanning everything else, so users know their results are incomplete.
- R8: Count each actual Python file only once, even if multiple symlinks point to it, so the final totals stay accurate.

# Round 3 requirements

- R9: Allow users to specify `--top N` to display only the N largest Python files, ranked by lines of code from highest to lowest, so they can quickly identify the biggest files in a large repository without scrolling through the entire report. The overall summary should still include all scanned files to ensure the repository statistics remain accurate.

# Round 4 requirements

- R5 changed: Previously, RepoLens automatically skipped a fixed list of unnecessary folders such as `.git`, `.venv`, `venv`, and `__pycache__`. Now, RepoLens should also respect the repository's `.gitignore` rules, including ignored files, folders, wildcard patterns, and nested `.gitignore` files, while continuing to skip the original default directories. This allows RepoLens to focus on the project's actual source code instead of generated files, dependencies, or temporary files, making its reports more accurate and useful.
