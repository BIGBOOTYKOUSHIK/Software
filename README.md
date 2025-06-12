# Memory Match Game

This is a simple memory matching game implemented with **Pygame**. The game features
multiple levels of increasing difficulty, local save data and two leaderboards
(best time and least moves). A new **Leaderboards** option on the main menu
shows the top 20 fastest times and lowest move counts. When you finish a level
and qualify for a leaderboard spot, you'll be asked to enter your name.

Run the game with:

```bash
python main.py
```

## Level Selection
A "Levels" button on the main menu opens a screen where you can choose from all ten levels. Locked levels appear grey and are unclickable until unlocked by completing earlier stages.

## Developer Mode
Press the small **Dev** button in the bottom-right corner of the menu or level screen. Enter `1 2 3 4 5` on the keypad and press **Submit** to unlock every level temporarily for testing.

The keypad shows digits in a familiar phone layout with a `0` key and larger **Submit** and **Cancel** buttons beneath. A **Menu** button appears on every screen so you can always return to the main menu. When Dev mode is active the button changes to **Normal** which restores your regular progress. The Normal button is slightly longer so the text fits neatly.

While playing in Dev mode, each card faintly shows its hidden value, allowing you to quickly test how the game behaves once all pairs are matched.

