# Kitaly — local homepage

A standalone homepage aligned to the existing Stock page: supplied crest, Cormorant Garamond and Libre Franklin, brass accents, warm cream, and a livelier club-green navigation rail.

Run from the repository root:

```sh
python3 -m http.server 4173 --bind 127.0.0.1
```

Open http://127.0.0.1:4173/local-home/ . All fonts and imagery are self hosted.

The Stock menu link points to http://127.0.0.1:5002/catalogue, the local Flask preview using an isolated temporary SQLite database and a sample inventory item. It must be running separately. This link is intentionally local; replace with the real relative catalogue route when integrating the homepage with Flask.

Includes working category and era filters, empty/reset states, product enquiry details, mobile navigation, founder quote, social links and sourcing email. The bag is an empty-state preview; no checkout integration. Policy links disclose missing copy. Alex's portrait awaits photography. Garment and social montage imagery is illustrative, not a live inventory or Instagram feed.

Photography: OpenAI ImageGen, recreated from the earlier generated asset. See assets/archive.jpg.json for provenance. Google Fonts original stylesheet is assets/fonts-source.css. Logo is the existing project artwork at static/images/brand-light.png.

Verification: desktop 1440px and mobile 390px screenshots in .impeccable/review/home-aligned-*.png; layout checked at 320px and 768px too. No deployment performed.
