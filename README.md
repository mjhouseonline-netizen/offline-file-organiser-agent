# Offline File Organiser Agent

One standalone offline agent with one job: organise files from a chosen folder into sorted folders. It never deletes files and it never overwrites existing files.

## What it does

- Defaults to the user's Desktop.
- Sorts into `Sorted Files` by type, date, project-like names, or instruction keywords.
- Shows a preview before moving anything.
- Moves files only with `shutil.move`.
- Creates conflict-safe names like `file (2).pdf`.
- Writes an undo log to `_organiser_logs`.
- Can undo the last sort from the saved manifest.

## Windows SmartScreen note

This first release is unsigned. Windows may show "Windows protected your PC" because the app does not have a paid code-signing certificate yet.

To run it:

1. Click **More info**.
2. Click **Run anyway**.

The app works fully offline, only moves files into folders, never deletes files, and never overwrites existing files.

## Instruction examples

```text
Sort my desktop into clear folders by file type. Keep screenshots together.
Put invoices, receipts, and tax files into Finance. Do not delete anything.
```

```text
folders: Finance, Photos, Work, Courses
invoices receipts tax -> Finance
course lessons modules -> Courses
ignore: shortcuts temp
```

## Build the standalone Windows exe

Double-click:

```bat
build-windows.bat
```

Output:

```text
dist\windows\Offline-File-Organiser-Agent.exe
```

The app is stdlib-only. PyInstaller is only needed for building the `.exe`.
