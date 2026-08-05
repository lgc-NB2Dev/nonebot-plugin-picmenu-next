---
status: accepted
---

# Keep Index-First Name and Pinyin Query

PicMenu Next treats a pure positive number as a 1-based menu index before attempting fuzzy matching; zero and all-zero queries remain fuzzy queries. Other queries combine the displayed name and its pinyin, with the name weighted at 60%, pinyin at 40%, and a score of 60 required to match. This gives users predictable direct selection while preserving Chinese and romanized discovery for names they do not enter exactly.
