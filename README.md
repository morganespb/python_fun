# idea bench

17 small sketches in python, all in one window. Use the left and right arrow keys to go from one to the next. They all use brown, black and silver, and one typeface.

## run

```
cd idea-bench
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py        # starts at sketch 0, then ← → to switch
python main.py 7      # starts at sketch 7
```

Each new terminal window needs `source .venv/bin/activate` again.

Keys everywhere: `←` `→` switch sketch, `esc` quits, `p` saves a png into `output/`, `h` hides the label, `f` goes fullscreen.

## folders

```
main.py           opens the window with every sketch
core/
  app.py          window, mouse, the loop, switching
  draw.py         canvas for particles, text, 3d projection, glow + grain
  noise.py        smooth noise
  palette.py      the six colours
  audio.py        tiny synth and a looping track
  camera.py       hidden webcam + mediapipe (hand, body)
  scroll.py       mouse wheel as a scroll bar
sketches/         one file per sketch, in order in sketches/__init__.py
fonts/            instrument serif (open font licence)
models/           mediapipe models
output/           your saved pngs and film frames
```

## the sketches

| # | sketch | try |
|---|---|---|
| 0 | unseen hand | 1 light, 2 sand, 3 smoke · pinch to lift · r rake · c camera check |
| 1 | smoke site | mouse wheel |
| 2 | product launch | mouse wheel |
| 3 | museum | drag, hover the rings |
| 4 | creature | move, hold the button |
| 5 | weather glass | move left / right |
| 6 | image dissolve | hover, click · `python main.py 6 photo.jpg` |
| 7 | kinetic type | brush the word · enter to type a new one |
| 8 | variable type | move near, move fast |
| 9 | visualiser | space · `python main.py 9 song.wav` |
| 10 | instrument | draw |
| 11 | seine | move left / right (sample data) |
| 12 | year in sound | hover (example data) |
| 13 | smoke mirror | walk past the camera |
| 14 | vj set | space, 1–4 |
| 15 | short film | click below the film · r renders frames |
| 16 | particle pet | move, click, wait |

## hand tracking tips

Press `c` in unseen hand to check what the camera sees. Detection works best:

- in even light, facing a window or a lamp, not with the light behind you
- with your palm open towards the camera, fingers spread
- 40–60 cm from the camera, with the whole hand in the picture
- against a plain background

The first time, macOS asks whether Terminal can use the camera. If you said no, turn it back on in System Settings → Privacy & Security → Camera.

## film from sketch 15

Press `r`, wait for 720 frames, then:

```
ffmpeg -framerate 30 -i output/film/%04d.png -pix_fmt yuv420p film.mp4
```

## test without a window

`BENCH_FRAMES=150 BENCH_SHOT=test.png python main.py 7` runs sketch 7 for 150 frames with a fake mouse, then saves the last frame.
