# GameShrink

GameShrink is a desktop application for analyzing large PC game installations, visualizing storage usage and creating isolated build workspaces.

The project is designed as a foundation for future game asset optimization research. Current versions focus on storage analysis, build planning and archive discovery while keeping the original game installation untouched.

## Features

Current

* Desktop GUI
* Command line interface
* Storage analysis
* Largest file and folder detection
* File extension statistics
* Interactive dashboard
* Storage heatmap
* Charts and visualizations
* Archive discovery
* Build planner
* Workspace generation
* Markdown reports
* Dark mode

## Safety

GameShrink never modifies the original game installation.

Every build is created inside a separate workspace so the original files remain untouched.

## Requirements

* Python 3.12 or newer
* Windows
* No external dependencies

## Running

Clone the repository.

```bash
git clone https://github.com/<your-username>/GameShrink.git
```

Open the project folder.

```bash
cd GameShrink/gameshrink
```

Launch the desktop application.

```bash
python gui.py
```

Run the command line scanner.

```bash
python main.py scan "<game folder>"
```

Generate a report from the command line.

```bash
python main.py report
```

Example

```bash
python main.py scan "C:\Program Files (x86)\Steam\steamapps\common\Max Payne 3"
```

## Project Structure

```text
GameShrink/
│
├── gameshrink/
│   ├── builder.py
│   ├── charts.py
│   ├── config.py
│   ├── gui.py
│   ├── heatmap.py
│   ├── main.py
│   ├── reporter.py
│   ├── scanner.py
│   ├── themes.py
│   ├── workspace.py
│   ├── plugins/
│   ├── reports/
│   └── workspace/
│
├── screenshots/
├── README.md
└── .gitignore
```

## Roadmap

Planned

* Archive adapters
* Archive browsing
* Archive extraction
* Archive rebuilding
* Texture optimization
* Audio optimization
* Build profiles
* Plugin SDK
* Additional archive format support

## Screenshots

Please note: The following is just a sample.

<img width="1916" height="1030" alt="image" src="https://github.com/user-attachments/assets/7230e24d-e6f3-4d56-bb04-5802a781e09d" />
<img width="1919" height="922" alt="image" src="https://github.com/user-attachments/assets/4b39ff42-39e0-4eae-9dab-13d5cd10063a" />
<img width="1919" height="985" alt="image" src="https://github.com/user-attachments/assets/76f7ed80-91c1-415d-885e-35498f4d4b73" />
<img width="1919" height="933" alt="image" src="https://github.com/user-attachments/assets/7e83840f-ac47-4bcb-94a7-28159a6a1d01" />



## Contributing

Issues, feature requests and pull requests are welcome.

## License

This project is currently under development.

A license will be added before the first stable release.
