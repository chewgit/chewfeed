# chewfeed
My first project, entirely vibecoded in ChatGPT Codex 5.4 and Claude Opus 4.6. A lightweight RSS feed to track latest updates from your favourite blogs with an inline plaintext reader.

Instructions to use:
1. On Github, click the big green button that says "<> Code". Select "Download ZIP"
2. Unzip it, wherever you've saved it to.
3. Run build.bat, it will create /dist/chewfeed.exe
4. Chewfeed/dist/chewfeed.exe is what you want to run
5. Should run nicely! If not message me on telegram
6. Core functionalities should be straightforward, you can Star your favourite feeds, the top navigation bar allows you to follow new feeds, and clicking a post in your feed opens a plaintext reader in the sidebar. 


Changelog
11/03/2026 - Changed parsing logic to so that blog posts are not parsed on a card by card basis, but rather a more scalable method. This is what ChatGPT Codex has to say:
Replace the current hard filter model with a candidate scoring + validation model, and only keep platform-specific adapters for truly common layouts like Newsletter Hunt or Substack.
So in short: yes, per-card filters are the wrong long-term direction. The scalable solution is a layered parser: structured feed -> platform adapter -> generic container scoring -> destination validation.


Future plans
1. Improve parsing logic for paywalled blog posts - can we build in archive.is functionality so the feed automatically checks archive.is for full text versions
