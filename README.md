# Memory Match Game

This is a simple memory matching game implemented with **Pygame**. The game features
multiple levels of increasing difficulty, local save data and two leaderboards
(best time and least moves). The **Leaderboards** option now first asks which
level you want to view. Each level keeps its own top 20 scores. When you finish
a level and qualify for a leaderboard spot, you'll be asked to enter your name.

Run the game with:

```bash
python main.py
```

## Level Selection
A "Levels" button on the main menu opens a screen where you can choose from all ten levels. Locked levels appear grey and are unclickable until unlocked by completing earlier stages.

## Viewing Leaderboards
Choose **Leaderboards** from the main menu to select which level's rankings to view. Each level maintains its own top 20 times and move counts.

## Developer Mode
Press the small **Dev** button in the bottom-right corner of the menu or level screen. Enter `1 2 3 4 5` on the keypad and press **Submit** to unlock every level temporarily for testing. When Dev mode is on, the button label changes to **Normal** so you can toggle it back off.

The keypad shows digits in a familiar phone layout with a `0` key and larger **Submit** and **Cancel** buttons beneath. A **Menu** button appears on every screen so you can always return to the main menu.

While playing in Dev mode, hidden cards display faint outlines of their values, making it easy to verify matches during development. Use this mode to reveal card numbers for debugging.

