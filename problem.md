# Problem

As a computer science student, I've noticed that understanding an unfamiliar codebase can be pretty overwhelming, especially when working on group projects or exploring open-source repositories on GitHub. It's not always obvious where to start, which files contain most of the logic, or how the project is structured. Going through every file manually takes time, and it's easy to miss important details. This can make it harder for students and new developers to understand a project, contribute to it, or make changes confidently.

# Initial requirements

- R1: The program should accept a folder path through the command line and scan all Python files inside that folder, including files in subfolders.
- R2: For each Python file, display its relative path and count the total lines of code, excluding blank lines and comments.
- R3: Count the functions and classes in each file, including asynchronous functions.
- R4: Display a summary at the end showing the total number of Python files scanned, lines of code, functions, and classes.
- R5: Automatically skip unnecessary directories such as .git, .venv, venv, and __pycache__.
- R6: Display a clear error message if the provided folder does not exist or cannot be accessed.
