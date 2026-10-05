# frogsdream compliance report

Date of this review: October 5, 2026. Site: frogsdream.com. Operator: Wojciech Niedźwiecki, Zwola 43, 26-920 Gniewoszów, Poland, a private individual running an unregistered activity (działalność nierejestrowana).

**Please read this first.** This report was prepared with AI assistance. It makes the site much safer, but it is not legal advice and it is not a lawyer's opinion. Laws and the rules of Google and Stripe change. If a lot of money or a complaint from an authority is ever involved, ask a Polish lawyer.

## 1. Summary

The site is now in good shape for a small, free site with one paid download:

* No page sends any data to another company while ads are off. The PDF library is now on our own server.
* The tools store nothing that needs consent. They keep your list only in the browser tab (session storage), never in cookies or permanent storage.
* The privacy policy now covers everything GDPR Article 13 asks for.
* The terms now work as a Polish "regulamin" (Article 8 of the act on electronic services), with a complaints procedure.
* The operator's name and address are shown on the privacy, terms and contact pages from one place in the code.
* Stripe Managed Payments is described correctly everywhere. Every Lemon Squeezy mention is gone.
* The Buy button is live with the Stripe link, and the product data for Google says InStock.
* The full QA passes.

Five decisions or tasks remain for you. They are in section 5.

## 2. What was checked, against which rule, and the result

| Area | Law or policy | Result |
|---|---|---|
| Requests to other companies | GDPR Art. 5, 6 and 44; German court rulings on Google Fonts (sending the IP address without a legal basis) | **Fixed.** jsPDF used to load from cdnjs (Cloudflare) when someone clicked Download PDF. It is now self-hosted. With ads off, no page requests anything from another host: no fonts, images, scripts, frames or styles. The QA now fails on any such request. |
| Cookies and on-device storage | ePrivacy Directive Art. 5(3); Polish Electronic Communications Law (Prawo komunikacji elektronicznej) Art. 399 | **Fixed.** Word lists, options and the bingo caller game moved from localStorage (permanent) to sessionStorage (cleared when the tab closes). This is "strictly necessary for a service the user asked for", so no consent is needed. The site sets no cookies of its own. Old localStorage keys from earlier versions are deleted automatically. The QA checks that no localStorage or cookie is written. |
| Storage before consent when AdSense is on | ePrivacy Art. 5(3); Google EU user consent policy | **OK.** Our scripts store only the tab-only tool input. Everything else is placed by Google's certified consent tool (CMP), which asks first. |
| Privacy policy content | GDPR Art. 13 | **Rewritten.** Controller name and address, contact, a table of purposes with legal basis and retention, server logs, emails, purchases, ads (only when switched on), storage, recipients, US transfers (Data Privacy Framework and standard contractual clauses), all rights, the right to complain to PUODO (ul. Stawki 2, 00-193 Warszawa, uodo.gov.pl), no automated decisions by us, Google's ad personalization explained with links, children, changes, and a fixed effective date. |
| Operator identification | Polish act on electronic services (UŚUDE) Art. 5; GDPR Art. 13(1)(a) | **Done.** Name and address are in `source/content/site.json` and appear on /privacy/, /terms/ and /contact/. |
| Terms (regulamin) | UŚUDE Art. 8 | **Rewritten.** Types and scope of services, technical requirements, ban on unlawful content, when the agreement starts and ends, complaints by email answered within 14 days, operator details, free licence, Mega Pack licence, Stripe and Link as seller, the 14-day refund promise, liability limits with "mandatory consumer rights are not affected", Polish law without removing consumers' home-country protection, and out-of-court help (Polish consumer ombudsmen, Trade Inspection, the UOKiK register, European Consumer Centres). |
| EU ODR platform link | Regulation (EU) 2024/3228 | **OK.** The platform closed on July 20, 2025. The terms say so and do not link to it. |
| Seller and price information | Consumer Rights Directive; Omnibus Directive; Polish consumer rights act | **Fixed.** The premium page, terms, download page and disclosure say the pack is sold through Stripe Managed Payments with Link as merchant of record, and that $7 includes taxes. Refund and licence wording is the same everywhere. |
| Stripe Managed Payments facts | Stripe documentation | **Checked** through web search (Stripe's own sites were blocked from this computer, so please glance at the checkout once). Stripe acts as merchant of record and handles tax, fraud, disputes and transaction support. Customers see purchases as "Sold through Link". The legal entity is Sold through Link, LLC (it was LemonSqueezy LLC before April 6, 2026). Link support handles payment and refund requests and may ask you first. |
| Product structured data | Google Merchant listing guidelines | **Changed.** Availability now comes from `packAvailable` in site.json. It is `true`, so the page says InStock. If it is ever set to false the page says OutOfStock (not PreOrder, which would claim people can order now). |
| Trademarks in word lists, prose and the Mega Pack | EU Trade Mark Regulation; US Lanham Act | **OK, no changes needed.** A sweep of all content files and the Mega Pack source for about 120 brand and character names found no brand used as a generic word. "Santa", "frosty", "frozen" and "trampoline" are ordinary words. Mentions such as "Google Classroom", "Chromebook" and "WordPress" only describe compatibility, which is allowed. The QA trademark list was extended (Pixar, Hot Wheels, Elf on the Shelf, Olympics, Kahoot, iPad, Netflix, Starbucks, Skittles, Peeps, Hershey's and others). |
| Font licence | SIL Open Font License 1.1 | **OK.** Fredoka is OFL with no Reserved Font Name and embedding flag 0 (installable). OFL.txt ships next to the font in `assets/fonts/`. Embedding the font in the Mega Pack PDFs is allowed; the PDFs are not covered by the font licence. |
| jsPDF licence | MIT | **OK.** The file keeps its licence header, and `assets/js/vendor/jspdf-LICENSE.txt` ships with it. |
| Mascot, icons and art | Copyright | **OK as far as can be checked.** All art is drawn by code in `source/art/` (hand-written shapes and paths). No third-party image files, icon sets or attributions were found. |
| Health claims (bedtime and potty pages) | Unfair Commercial Practices Directive; honesty rules in the spec | **Improved.** Sleep hours cite the AASM consensus (endorsed by the AAP). A short "not medical advice" note was added to the 4 bedtime chart pages and the potty training and behavior chart pages, and the school-age sleep answer now links to the AASM source. The guide and tool page already had the note. |
| Outdoor scavenger hunt safety | General duty of care | **OK.** All 18 hunts have a safety section (supervision, staying in sight, no picking plants, water, roads). The terms say adults are responsible for supervision. |
| Paid bingo (gambling) | Polish Gambling Act; UK Gambling Act; US state laws | **Improved.** Two guides and the terms now say that charging players or offering cash prizes can make bingo regulated gaming, so check local rules. "Payout" wording was removed. |
| Children and COPPA | COPPA (US); GDPR Art. 8; AdSense child-directed rules | **OK.** All copy addresses adults. The privacy policy says the site is for adults and we don't knowingly collect children's data. The owner guide says not to mark the site as child-directed. Note: some themes (sight words, toddler charts) are about children, so Google could still treat some pages as mixed audience. That would only limit ad personalization, not break rules. |
| AdSense placement | AdSense program policies | **OK.** No ads inside tools, at least 150px from buttons, never in print. No ads on the embeds, bingo caller, premium, download, privacy, terms, contact and error pages. The QA tests all of this with a dummy AdSense ID. |
| Hidden download page | Privacy and search | **OK.** noindex and nofollow in the page and in an X-Robots-Tag header (this also covers the zip), no ads, no tracking, not in the sitemap. Anyone who has the link can download the zip; that is an accepted risk for a $7 pack. |
| External links | Security best practice | **OK.** Every external link has rel="noopener" (checked by QA). |
| Email obfuscation | Spam protection | **OK.** The address is assembled by JavaScript, with "hello at frogsdream dot com" as the fallback. The QA checks it works. |
| AI disclosure | Spec owner override 2; EU AI Act Art. 50 (not strictly required for edited text, but honest) | **OK.** The About page says content was written with AI assistance and reviewed for accuracy, and does not claim a person checked it. |
| Accessibility | European Accessibility Act (Directive 2019/882), Polish act of April 26, 2024 | **Exempt, but good practice is followed.** Micro-enterprises (fewer than 10 people and under EUR 2 million turnover) that provide services are exempt. The site still targets WCAG 2.1 AA and Lighthouse checks accessibility at 95+. |

## 3. What was changed

**Code and build**

* `source/static/assets/js/vendor/jspdf.umd.min.js` (jsPDF 2.5.1, licence header kept, source map line removed) and `jspdf-LICENSE.txt` added. `pdf.js` loads it from our own server.
* `toolkit.js` and `caller.js` use sessionStorage instead of localStorage. `site.js` deletes leftover `fd:` keys from localStorage, and hides or shows the Mega Pack lines according to `PACK_URL`.
* `source/content/site.json` has new entries: `operator` (name and address, the single source of truth), `legal.updated` (policy date), `packAvailable` (true).
* `build.py` fills `{{OPERATOR_NAME}}`, `{{OPERATOR_BLOCK}}` and `{{POLICY_DATE}}`, sets the Product availability from `packAvailable`, prints a WARNING when the operator name is empty, and writes the Buy buttons and Mega Pack lines into the HTML already live when the shipped `config.js` has a `PACK_URL`.
* `config.js` ships with `PACK_URL` set to `https://buy.stripe.com/6oU5kD4iYeTr5eJ4oN7kc05`.

**QA (made stricter, nothing weakened)**

* Browser tests no longer route cdnjs. Any request to another host now fails, including during Download PDF.
* New checks: no localStorage or cookies after using the tools; no third-party resources in any page, CSS or script; jsPDF and font licences present; no Lemon Squeezy mention; download page noindex and ad-free; operator name and address on the three legal pages, with a WARNING (not a failure) while the name is empty.
* The `config.js` check accepts `PACK_URL` empty or a `https://buy.stripe.com/` link. ADSENSE_CLIENT, AD_SLOT_IN_ARTICLE and TIP_URL must still be empty.
* The config browser test now has three parts: the config exactly as shipped (Buy buttons live with the Stripe link, no "Coming soon", no third-party requests), an injected empty config, and an injected dummy config.
* The old `source/qa/vendor` copy of jsPDF was removed because it is no longer needed.

**Content**

* Privacy policy, terms, premium page, contact page, disclosure page and the hidden download page rewritten or updated as described above.
* Tool pages no longer promise that lists survive closing the tab.
* Bedtime, potty and behavior chart pages: not-medical-advice notes; AASM link on the school-age page.
* Bingo guides: note on paid bingo and local gaming rules.
* Mega Pack "Start here" PDF: points to the full terms and repeats the 14-day fix-or-refund promise. The pack was rebuilt; only that PDF and the zip changed.

**Owner documents**

* `OWNER-README.html`: Stripe Managed Payments setup checklist, upload of the zip into the hidden folder, name and address already built in, Stripe link already built in, only `ADSENSE_CLIENT` left to paste later. The lessoncorner and backup steps are unchanged.
* `README.md`, `source/SPEC.md` (new owner override 6), `source/TOOL-CONTRACT.md` and `source/CONTENT-FORMAT.md` updated the same way.

## 4. Decisions already made

* **Publishing your address (UŚUDE Art. 5).** Decided: you chose to publish Zwola 43, 26-920 Gniewoszów, Poland. It is shown on the privacy, terms and contact pages. This fully meets Article 5 for a natural person.

## 5. Decisions and tasks only you can do, with recommendations

1. **Check the Stripe checkout once.** Make one test purchase and confirm the checkout says "Sold through Link", that tax is included in $7, and that you land on the download page. If the checkout shows a different seller name, tell Claude so the pages can match it exactly. *Recommendation: do this before you promote the site.*
2. **Upload the Mega Pack zip** into `public_html/pack-download-b0b5f94d131b/` without extracting it. Until you do, buyers would reach a broken download link. *Recommendation: do it right after uploading the website.*
3. **One review by a Polish lawyer.** *Recommendation: yes, once, before or soon after the first sales.* A one-hour review of the privacy policy and terms costs little and covers things an AI cannot promise, for example whether you also need a Polish-language regulamin for Polish consumers (the law does not require one for an English-language service, but practice varies).
4. **Taxes and the działalność nierejestrowana limit.** The 2026 limit is 10,813.50 PLN of revenue per quarter. If you go over it, you must register a business within 7 days. *Recommendation: ask an accountant once about (a) how to report Stripe payouts and AdSense on your yearly PIT, (b) whether AdSense income from Google Ireland means you must register for VAT-UE and file VAT-UE summaries even though you are VAT-exempt (this is a common requirement for Polish AdSense earners), and (c) how to treat Stripe payouts, given that Link, a US company, is the seller and you supply it.* Keep a simple income spreadsheet from day one.
5. **Email forwarding.** The privacy policy says that if you forward hello@frogsdream.com to Gmail, Google stores a copy. That is accurate either way. *Recommendation: if you forward, keep it; if you use only the Hostinger mailbox, nothing changes.* Delete old emails after two years, as the policy promises.
6. **When you switch on AdSense:** publish the European consent message in AdSense (Privacy & messaging) before or at the same time as you paste `ADSENSE_CLIENT`, and do not mark the site as child-directed. The privacy policy already describes ads "only while switched on", so no text change is needed. *Recommendation: also update `legal.updated` in site.json and rebuild so the policy date shows the change.*

## 6. Known limits of this review

* Stripe's and Hostinger's own websites could not be opened from the build computer; their facts come from search results and their public policies. Hostinger's log retention period and data center location were not confirmed, so the policy describes them in general terms.
* The originality of the art was checked by looking at how it is made (all drawn by code), not by a reverse image search.
* This report reduces risk. It does not guarantee that no authority, court or platform will see things differently.
