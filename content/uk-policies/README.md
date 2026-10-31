# UK policy pages

Prepared 31 October 2026 for Kitaly, a UK-based seller.

`contact-us.txt` contains the existing production contact details and is ready to publish. The four other files are private drafts with explicit `[CONFIRM: ...]` markers. Existing information pages are preserved.

Run `venv/bin/python scripts/prepare_uk_policy_pages.py` to preview the import, or add `--apply` to save missing pages. Re-running skips existing slugs and never overwrites edits. The page editor blocks publication while draft markers remain. Draft previews require an admin login, are not indexed and are not cached.

Before publishing the drafts, confirm:

- Legal seller/data controller name, business and return addresses, trading status, company and VAT details if applicable.
- Shipping destinations, fees, dispatch and transit times, tracking and international customs arrangements.
- Change-of-mind return postage, exchange policy, order acceptance process and complaints handling.
- Hosting, email and delivery providers; international data transfers and safeguards; retention rules and any marketing or automated decision-making.

## Cookie/storage review

The checked catalogue code contains no visitor analytics or advertising pixels. It uses a Flask session cookie, language selection and `localStorage.theme`. The new cookie preferences page explains these and lets visitors object to saving appearance preferences. Opting out removes the saved theme and language without deleting essential checkout/order session data. A one-year `appearance_preferences` cookie honours that choice. Turning off saving does not disable the visible theme switch.

External resources currently include Google Fonts, Tailwind CDN and unpkg. Stripe and contact destinations have their own processing. This review does not audit those services' internal storage or the seller's off-site processes. Reassess before adding analytics, embeds or marketing tags; a preference control for appearance does not authorise tracking.

## Sources checked

- [UK distance selling information requirements](https://www.gov.uk/online-and-distance-selling-for-businesses)
- [UK returns and refunds guidance](https://www.gov.uk/accepting-returns-and-giving-refunds)
- [Consumer Contracts Regulations, cancellation and refunds](https://www.legislation.gov.uk/uksi/2013/3134/part/3)
- [Consumer Rights Act guidance](https://www.gov.uk/government/publications/consumer-rights-act-2015/consumer-rights-act-2015)
- [ICO storage/access exceptions, including appearance preferences](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guidance-on-the-use-of-storage-and-access-technologies/what-are-the-exceptions/)
- [ICO data protection guidance](https://ico.org.uk/media/for-organisations/guide-to-the-general-data-protection-regulation-gdpr-1-1.pdf)

The pages are written for this shop; the reference retailer's policy text was not copied. Missing business facts prevent the drafts from being complete publication-ready policies.
