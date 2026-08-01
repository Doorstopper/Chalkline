# Putting Chalkline on your phone

Six files. Upload them somewhere with an https address, then add it to your home
screen. Fifteen minutes, free, and you never open Claude to use it again.

    index.html              the app
    sw.js                   makes it work with no signal
    manifest.webmanifest    makes it install like an app
    icon-192.png
    icon-512.png
    apple-touch-icon.png

Keep the filenames exactly as they are. `index.html` in particular — that's what
makes the address work without a filename on the end.

---

## GitHub Pages (recommended)

Permanent, free, and you can do the whole thing from the phone if you want.

1. Sign in at **github.com** (create an account if you haven't got one).
2. **New repository** → name it `chalkline` → **Public** → Create.
3. On the repo page: **Add file → Upload files**. Drag all six in. Commit.
4. **Settings → Pages**. Under *Build and deployment*, set Source to
   **Deploy from a branch**, branch `main`, folder `/ (root)`. Save.
5. Wait two or three minutes. The address appears at the top of that same page:

       https://YOURNAME.github.io/chalkline/

### On the repo being public

Anyone with the address can open the app. That's fine — it's just the tool. No
video, no marks, no names are in these files, and nothing you do in the app is
sent anywhere. Private repos need a paid plan for Pages, and there's nothing here
worth paying to hide.

The one thing that *is* worth guarding is your live-sync session name, if you set
one up. Anyone who guesses it can read your marks. Use round numbers, not
players' surnames.

## Netlify Drop (faster, less permanent)

If you just want it working in two minutes: go to **app.netlify.com/drop** and
drag the folder in. You get an address immediately with no account. Make an
account within 24 hours or it disappears.

---

## Adding it to your home screen

**iPhone.** Open the address in **Safari** (not Chrome — only Safari can install
on iOS). Share button → **Add to Home Screen**. It appears with the Chalkline
icon and opens full-screen with no browser bars, straight to the Sideline tab.

**Android.** Open in Chrome. You should get an *Install app* prompt; if not, the
three-dot menu has **Add to Home screen**.

## Working with no signal

After the first visit the whole app is cached on the phone. At a ground with one
bar or none, it opens and tags exactly the same — you'll get a brief *Offline*
note and nothing else changes. If live sync is on, it simply waits until you're
back in range.

Test it before you rely on it: open the app once on wifi, put the phone in
aeroplane mode, then open it again from the home screen. It should load normally.

## Updating it later

Upload the new `index.html`, then open `sw.js` and change `chalkline-v1` to
`chalkline-v2`. Without that bump, phones keep serving the cached old version and
you'll wonder why nothing changed. Bump the number every time you change the app.

## Pointing the desktop shortcut at it

Open `Create Chalkline shortcut.cmd` in Notepad, fill in the `SITE=` line with
your new address, and run it again. Both devices then run the same copy, which is
what you want once sync is on.
