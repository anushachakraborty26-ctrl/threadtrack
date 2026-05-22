// ThreadTrack — Process Documentation builder
// Regenerate any time: `node build.js`  → outputs ../ThreadTrack_Process_Documentation.docx
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, TableOfContents, PageBreak, PageNumber, Header, Footer
} = require('docx');

const CONTENT_W = 9360; // US Letter, 1" margins

// ---------- helpers ----------
const t  = (s) => new TextRun(String(s));
const b  = (s) => new TextRun({ text: String(s), bold: true });
const it = (s) => new TextRun({ text: String(s), italics: true });

function p(children) {
  const kids = typeof children === 'string' ? [t(children)] : children;
  return new Paragraph({ children: kids, spacing: { after: 140 }, alignment: AlignmentType.JUSTIFIED });
}
function h1(s) { return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [t(s)] }); }
function h2(s) { return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [t(s)] }); }
function h3(s) { return new Paragraph({ heading: HeadingLevel.HEADING_3, children: [t(s)] }); }
function bullet(children) {
  const kids = typeof children === 'string' ? [t(children)] : children;
  return new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: kids, spacing: { after: 70 } });
}
function pageBreak() { return new Paragraph({ children: [new PageBreak()] }); }

function callout(label, body) {
  const border = { style: BorderStyle.SINGLE, size: 4, color: 'E6A23C' };
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [CONTENT_W],
    rows: [ new TableRow({ children: [ new TableCell({
      width: { size: CONTENT_W, type: WidthType.DXA },
      shading: { fill: 'FCF3E3', type: ShadingType.CLEAR },
      borders: { top: border, bottom: border, left: border, right: border },
      margins: { top: 140, bottom: 140, left: 180, right: 180 },
      children: [
        new Paragraph({ children: [new TextRun({ text: label, bold: true, color: '9A6212' })], spacing: { after: 70 } }),
        new Paragraph({ children: [it(body)] }),
      ],
    }) ] }) ],
  });
}

function table(headers, rows, widths) {
  const bd = { style: BorderStyle.SINGLE, size: 1, color: 'C9D2DC' };
  const borders = { top: bd, bottom: bd, left: bd, right: bd };
  const head = new TableRow({
    tableHeader: true,
    children: headers.map((hd, i) => new TableCell({
      borders, width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: '2E5B8A', type: ShadingType.CLEAR },
      margins: { top: 90, bottom: 90, left: 130, right: 130 },
      children: [ new Paragraph({ children: [new TextRun({ text: hd, bold: true, color: 'FFFFFF' })] }) ],
    })),
  });
  const body = rows.map((r, ri) => new TableRow({
    children: r.map((c, i) => new TableCell({
      borders, width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: ri % 2 === 0 ? 'F2F5F8' : 'FFFFFF', type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 130, right: 130 },
      children: [ new Paragraph({ children: [t(c)] }) ],
    })),
  }));
  return new Table({ width: { size: widths.reduce((a, x) => a + x, 0), type: WidthType.DXA }, columnWidths: widths, rows: [head, ...body] });
}
const spacer = () => new Paragraph({ children: [t('')], spacing: { after: 80 } });

// ---------- document content ----------
const body = [];

// ===== TITLE PAGE =====
body.push(new Paragraph({ children: [t('')], spacing: { before: 2600 } }));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
  children: [new TextRun({ text: 'ThreadTrack', bold: true, size: 72, color: '2E5B8A' })] }));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 },
  children: [new TextRun({ text: 'Process Documentation', bold: true, size: 36, color: '444444' })] }));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
  children: [new TextRun({ text: 'An honest, complete record of building a supply chain', italics: true, size: 26, color: '666666' })] }));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 },
  children: [new TextRun({ text: 'risk-prediction system from zero.', italics: true, size: 26, color: '666666' })] }));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
  children: [new TextRun({ text: 'Project and documentation by Anusha Chakraborty', size: 24 })] }));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
  children: [new TextRun({ text: 'National Institute of Fashion Technology', size: 22, color: '666666' })] }));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 },
  children: [new TextRun({ text: 'Covering 19-23 May 2026 — Phases 1 to 5 complete, Phase 6 in progress', size: 22, color: '666666' })] }));
body.push(new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'This document is written so a reader with no prior knowledge of supply chains, data analysis,', size: 20, color: '888888' })] }));
body.push(new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'or programming can follow every step. It is updated at the end of each work session.', size: 20, color: '888888' })] }));
body.push(pageBreak());

// ===== TABLE OF CONTENTS =====
body.push(h1('Table of Contents'));
body.push(new TableOfContents('Table of Contents', { hyperlink: true, headingStyleRange: '1-2' }));
body.push(pageBreak());

// ===== HOW TO READ =====
body.push(h1('How to Read This Document'));
body.push(p('This is not a polished sales brochure. It is a working logbook of a real project, written while the project was still being built. It records what went right, what went wrong, what was thrown away, and what was learned. It is deliberately honest about mistakes, because the mistakes are where the real learning happened.'));
body.push(p('Every technical idea is explained from its foundations. Where a specialised word is unavoidable, it is defined the first time it appears, and again in the Glossary at the end. The language is professional and precise, but nothing is assumed. If you have never written a line of code or seen a supply chain, you can still finish this document understanding both.'));
body.push(p('The document has three kinds of sections. The early sections (1 to 5) explain what the project is and how it is designed. Section 6, the Daily Log, is the heart: a day-by-day account of the actual work. The later sections (7 to 11) are reference material that go deeper on resources, code, and lessons.'));
body.push(callout('A note on honesty', 'Throughout this document, shaded boxes like this one mark moments of difficulty, error, or doubt. They are included on purpose. A project that appears to have gone perfectly is either trivial or dishonestly described. This one was neither.'));
body.push(pageBreak());

// ===== SECTION 1 =====
body.push(h1('1. Introduction: The Problem We Set Out to Solve'));

body.push(h2('1.1 What is a supply chain?'));
body.push(p('A supply chain is the complete journey a physical product takes, from raw material to the moment it reaches the customer who ordered it. Every business that makes and sells a physical object has one. A bakery has a supply chain: wheat is grown, milled into flour, delivered to the bakery, baked into bread, and handed to a customer. A car manufacturer has an enormously complex one. The principle is identical at every scale: materials move through a sequence of steps, and at the end a finished product is delivered.'));
body.push(p('Three things flow along a supply chain at once. Materials flow forward (raw inputs becoming finished goods). Information flows in both directions (orders, schedules, confirmations, complaints). Money flows backward (the customer pays, and that payment travels back up the chain). When people say a supply chain is "working well," they mean all three flows are smooth, predictable, and on time.'));
body.push(p('ThreadTrack focuses on one specific kind of supply chain: the production and delivery of clothing for online-first fashion brands. The choice of industry is deliberate, but the ideas in this project are general. A delay-prediction system for clothing uses exactly the same logic as one for electronics, furniture, or groceries. The skill being demonstrated is the analysis, not the industry.'));

body.push(h2('1.2 What is a "delay," and why does it cost money?'));
body.push(p('A delay is simple to state: a product arrives later than it was promised to arrive. But "later than promised" has layers. A factory can miss the date it promised to finish production. A shipment can take longer than expected to travel. A customer can receive their order after the date they were told to expect it. The worst layer is the commercial one: a product can arrive after the window in which anyone wants to buy it. A winter coat that arrives in summer has not merely been delayed; it has, for business purposes, been destroyed.'));
body.push(p('Delays cost money in two ways. The direct costs are visible: refunds, the expense of fast emergency shipping to catch up, the staff time spent handling complaints. The indirect costs are larger and harder to see: a customer who cancels, a customer who never orders again, and a public one-star review that quietly discourages dozens of future customers. A business that cannot predict its delays is forced to absorb all of these costs reactively, after the damage is already done.'));

body.push(h2('1.3 What is a "return," and how is it connected to delays?'));
body.push(p('A return is when a customer sends a delivered product back. Returns are an enormous problem for online clothing in particular, because a customer cannot touch the fabric or try the garment on before buying. Industry data gathered for this project shows that roughly one in five online fashion orders in India is returned, and for the worst-performing businesses the figure approaches one in three.'));
body.push(p('There is a connection between delays and returns that is easy to miss and important to understand. Delayed orders are returned more often than on-time orders. The reasons are human: the customer needed the item for a specific occasion that has now passed; the customer has mentally moved on; the customer, tired of waiting, bought a replacement elsewhere and no longer needs two. This means a delay does not simply cause a delay. It also quietly raises the chance of a return. A system that predicts only delays therefore misses part of the financial damage. ThreadTrack predicts both, on purpose.'));

body.push(h2('1.4 Why predict these things at all?'));
body.push(p('Most businesses handle delays and returns reactively: a problem occurs, and then it is dealt with. Prediction changes the order of events. If a business can look at an order on the day it is placed and estimate the probability that it will be late or returned, it can act before anything has gone wrong. It can place the order with a more reliable supplier, build in extra time, hold a small safety stock, or simply warn the customer early and honestly. Prediction converts a fire-fighting operation into a planning operation. That conversion is the entire purpose of ThreadTrack.'));
body.push(pageBreak());

// ===== SECTION 2 =====
body.push(h1('2. What ThreadTrack Is'));

body.push(h2('2.1 The project in one sentence'));
body.push(p([b('ThreadTrack is a system that looks at a clothing purchase order on the day it is placed and predicts two things: the probability that it will be delivered late, and the probability that it will be returned, with a plain-English explanation of every reason behind each prediction.')]));

body.push(h2('2.2 What it actually does, step by step'));
body.push(p('Stripped to its essentials, ThreadTrack performs the following sequence:'));
body.push(bullet('It takes in the details of a single purchase order: which supplier is making it, what kind of fabric, the order size, the destination city, the payment method, the season, and so on.'));
body.push(bullet('It passes those details through a hand-built scoring system, designed from supply chain domain knowledge, which adds up risk points and produces a delay score and a return score, each from 0 to 100.'));
body.push(bullet('It also passes the same details through a machine learning model, which has learned risk patterns from thousands of past orders rather than from hand-written rules.'));
body.push(bullet('It combines the two estimates into a single, more trustworthy prediction.'));
body.push(bullet('For every prediction, it produces a written list of the specific reasons the order was flagged, so a human can read and judge the reasoning rather than being asked to trust a black box.'));

body.push(h2('2.3 What ThreadTrack is not'));
body.push(p('Honesty about scope is part of good engineering. ThreadTrack is a portfolio project, and several things about it are deliberately limited.'));
body.push(bullet('It does not use a real company’s private order data. No such data is publicly available. Instead it uses a synthetic (artificially generated) dataset, carefully calibrated so its statistical patterns match real, cited industry figures. Section 4 explains this choice in full.'));
body.push(bullet('It is not, at the time of writing, a finished deployed product. It is being built in phases; five of the six are complete, and the sixth — which turns the working system into usable tools — is well under way.'));
body.push(bullet('It does not claim perfect accuracy. As later sections show in detail, one of its two predictions works very well and the other is genuinely difficult, and the project says so plainly rather than hiding it.'));
body.push(pageBreak());

// ===== SECTION 3 =====
body.push(h1('3. Who ThreadTrack Is For'));

body.push(h2('3.1 The functional user: the buying merchant'));
body.push(p('Imagine the person inside a clothing brand whose job is to decide which supplier makes which order, and when. In the industry this role is called a buying merchant or a supply chain analyst. This person places dozens or hundreds of orders, and cannot possibly hold the full risk picture of each one in their head. ThreadTrack is designed as a tool for exactly this person. It is built to fit their workflow: it ranks the orders that need attention, explains why each one is risky in language they already use, and leaves the final decision to them. It is an assistant, not a replacement.'));

body.push(h2('3.2 The real audience: a hiring manager'));
body.push(p('There is a second, equally important audience. ThreadTrack is a portfolio project. Its purpose is to demonstrate, to a person deciding whether to hire its author, a concrete and complete piece of applied work. The author is a student transitioning into a technology career, and the skills the project is built to evidence are general and transferable: gathering and judging data sources, generating and validating a dataset, designing a transparent scoring model, training and honestly evaluating a machine learning model, and writing clearly about all of it.'));
body.push(p('This dual audience explains many decisions recorded later in this document. When a choice had to be made between something that looked impressive and something that was honest and well-reasoned, the project consistently chose the second. A hiring manager who reads carefully is far more convinced by sound judgment than by inflated claims.'));
body.push(pageBreak());

// ===== SECTION 4 =====
body.push(h1('4. The Architecture and Logic'));
body.push(p('"Architecture" here means the overall shape of the system: what its parts are, and how information flows between them. ThreadTrack is best understood as a pipeline — a sequence of stages, where the output of each stage becomes the input of the next.'));

body.push(h2('4.1 The pipeline, end to end'));
body.push(p('The flow of the whole system is as follows:'));
body.push(bullet('Cited industry research is gathered and distilled into a single reference document of benchmark numbers.'));
body.push(bullet('Those numbers are used to generate a synthetic dataset of purchase orders whose statistical behaviour mirrors reality.'));
body.push(bullet('The hand-built rule-based scorer reads each order and produces transparent risk scores.'));
body.push(bullet('The machine learning model reads the same orders and produces its own, pattern-learned risk estimates.'));
body.push(bullet('The two are blended into a single hybrid score.'));
body.push(bullet('A language-model layer reads unstructured customer reviews and extracts supply chain complaints, providing an independent real-world check.'));
body.push(bullet('Finally, an output layer presents everything through a spreadsheet tool, an interactive dashboard, and a written case study.'));

body.push(h2('4.2 The data layer, and why the data is synthetic'));
body.push(p('A prediction model learns from examples. To build one, the project needed a large table of past orders, each marked with whether it was eventually delayed or returned. No clothing brand publishes such private operational data. The project therefore generates its own.'));
body.push(p('This raises an obvious and serious objection: if the data is invented, is the model not simply learning patterns that the author invented? This objection is correct, and it was taken seriously from the start. The answer is calibration. The synthetic data is not invented freely. Every statistical setting that shapes it — how often orders are late, how returns vary by payment method, how long production takes — is drawn from real, cited industry figures collected in the research phase. The data is artificial in origin but realistic in shape. Section 6 records the calibration process in detail, including the fact that the very first version of the data was badly wrong and had to be corrected three times.'));

body.push(h2('4.3 The two-tier model, and why there are two'));
body.push(p('ThreadTrack does not use one prediction method. It uses two, deliberately, because they have opposite strengths.'));
body.push(p([b('Tier one is the rule-based scorer. '), t('This is a system of hand-written rules, designed from supply chain knowledge. Each risk factor adds a fixed number of points. Its great strength is transparency: every prediction can be explained, line by line, in plain language. Its weakness is that it can only contain knowledge the designer already has; it cannot discover anything new.')]));
body.push(p([b('Tier two is the machine learning model. '), t('This is an algorithm that examines thousands of past orders and finds patterns on its own. Its strength is that it can discover subtle combinations of factors a human would never think to write down. Its weakness is that it is a "black box": it is hard to explain why it made any single prediction.')]));
body.push(p('Used together, the two cover each other’s weaknesses. When both agree that an order is risky, confidence is high. When they disagree, the order is flagged for a human to look at closely. This rules-plus-learning combination is how serious real-world decision systems are actually built; it is not a student simplification.'));

body.push(h2('4.4 The language-model layer'));
body.push(p('A third source of insight is now built. Customer reviews are written in ordinary language and contain supply chain signals that no neat data column captures: "it arrived too late," "the fabric felt cheap," "the size was wrong." A large language model reads these reviews automatically and converts them into structured categories. As Section 6 explains, the Phase 4 results had made the value of this layer clear in advance: returns proved hard to predict from order data alone, and customer text is precisely the missing source of signal. Phase 5 built this layer and used it to check the whole model against independent real-world evidence.'));

body.push(h2('4.5 The output layer'));
body.push(p('The final phase makes the system usable and presentable. Two of its three parts are now built: a spreadsheet-based tool of the kind supply chain analysts use daily, and a lightweight interactive dashboard that runs in a web browser. The third part — a written case study tying the whole project together — remains to be written, as does the step of putting the dashboard online at a public address. Section 6 records this work in detail.'));
body.push(pageBreak());

// ===== SECTION 5 =====
body.push(h1('5. The Work Plan: Six Phases'));
body.push(p('Before any building began, the work was divided into six phases. Each phase produces something concrete and testable before the next begins. This document covers Phases 1 to 5 in full, and the work of Phase 6 completed so far.'));
body.push(spacer());
body.push(table(
  ['Phase', 'Name', 'What it produces', 'Status'],
  [
    ['1', 'Foundation', 'Working tools, a code repository, and a researched benchmark document', 'Complete'],
    ['2', 'Synthetic data', 'A calibrated 5,000-order dataset and an exploratory analysis', 'Complete'],
    ['3', 'Rule-based scorer', 'A transparent 15-factor risk scorer and its documentation', 'Complete'],
    ['4', 'Machine learning model', 'Trained delay and return models, blended with the rule scorer', 'Complete'],
    ['5', 'Language-model layer', 'Automated review analysis and independent model validation', 'Complete'],
    ['6', 'Output layer', 'Spreadsheet tool, dashboard, and written case study', 'In progress'],
  ],
  [820, 2200, 4540, 1800]
));
body.push(spacer());
body.push(callout('On the difference between plan and reality',
  'The six-phase plan was estimated at roughly six weeks of part-time work. In practice the first four phases were completed in about three intense days. This is recorded not as a boast but as a fact relevant to anyone reading the daily log: the days described below were long, and the speed introduced its own mistakes.'));
body.push(pageBreak());

// ===== SECTION 6 — DAILY LOG =====
body.push(h1('6. The Daily Log: What Actually Happened'));
body.push(p('This section is the core of the document. It records the actual work, day by day, in the order it happened, including every significant error and how it was resolved. The phases above are tidy. The days below were not. Both are true at once, and that is the point.'));

// --- Day 1 ---
body.push(h2('6.1 Day One — Setting Up the Workshop'));
body.push(p('The first day produced no part of the actual product. It was spent entirely on preparation: installing tools and creating the place where the work would live. This is normal and necessary. One cannot build without a workbench.'));
body.push(h3('What was done'));
body.push(p('The day began by checking what tools were already present on the computer. Two were: a programming language called Python, and a version-tracking tool called Git. One was missing: a tool called Homebrew, which acts as an installer for other developer software. Homebrew was installed first.'));
body.push(p('Next came a code editor called Visual Studio Code — the program in which code is actually written and read. After that, a code repository was created. A repository ("repo") is a project folder whose entire history of changes is tracked, so any past version can be recovered. The repository was named "threadtrack," created on a service called GitHub (an online home for repositories), and copied down to the computer. Inside it, a tidy folder structure was created — separate folders for data, code, notebooks, documents, and outputs — and a README file was written to describe the project. The day ended with the first "commit": a permanently saved snapshot of the work, uploaded to GitHub.'));
body.push(h3('Errors and setbacks'));
body.push(callout('The Homebrew installer "panic"',
  'When the Homebrew installer ran, it printed a long, fast-scrolling wall of technical text. With no prior experience, this was alarming — it looked like something was badly wrong. Nothing was. The installer was simply listing, politely, every file it was about to create, and waiting for confirmation. The lesson, which recurred throughout the project: a wall of text is usually information, not an error. An actual error names itself.'));
body.push(p('A second snag involved a keyboard command. To register a shortcut, an instruction had to be typed into a search bar inside the code editor. It was instead typed into the terminal — a different window entirely — which did not understand it. The underlying lesson is one every beginner learns once: a command only works in the specific program it belongs to. The terminal and the editor are different places.'));
body.push(p('Finally, the first attempt to save work to GitHub failed twice. Once because of a simple typo — the word "git" was accidentally written twice as "gitgit." Once because the save command was run from the wrong folder, before navigating into the project. Both were corrected in seconds once understood. They are recorded because they are exactly the kind of small friction that makes a first day feel harder than it is.'));
body.push(h3('What Day One produced'));
body.push(p('Nothing visible — and everything necessary. By the end of the day there was a working set of tools, an organised project folder, a safe system for saving progress, an online backup, and a professional-looking front page. The foundation every later day would stand on.'));

// --- Day 2 ---
body.push(h2('6.2 Day Two — An AI Account and the Raw Research'));
body.push(p('Day Two had two goals: open an account that would later allow the project to use an AI service automatically, and gather the raw industry research the whole project would be built on.'));
body.push(h3('What was done'));
body.push(p('The first task was to register for the Anthropic API. An API, in plain terms, is a service window through which one program can make requests to another. A later phase of ThreadTrack needs to send hundreds of customer reviews to an AI for automatic analysis; that requires a paid account set up in advance. The account was created and a small amount of credit, twenty US dollars, was added to it.'));
body.push(p('The second task was research. Three substantial industry reports were located and downloaded: a global fashion-industry report from a major consultancy, a report on India’s online direct-to-consumer retail sector, and the annual report of India’s government Ministry of Textiles. These three were chosen to cover three different layers of context — global, national, and governmental — a choice explained fully in Section 7.'));
body.push(h3('Errors and setbacks'));
body.push(p('Setting up the payment for the AI account did not work at first. The "buy" button stayed disabled, and the tax field showed only dashes instead of a number. The cause was eventually traced to the web browser. The privacy-focused browser in use was blocking scripts that the payment processor needed to calculate tax. Switching to a different, more conventional browser solved it immediately. The lesson: when an online form behaves strangely for no clear reason, the browser itself is a suspect worth testing.'));
body.push(callout('The security incident: a leaked key',
  'After the account was created, it produced an API key — a long secret password that grants access to the paid service. This key was, by mistake, pasted directly into a chat window. This is one of the most common and most serious mistakes a new developer can make: anyone who obtains such a key can spend the account’s money and act in its name. The error was caught within seconds. The leaked key was immediately revoked (permanently disabled), a fresh key was generated, and the new key was stored privately and never shared again. The mistake cost nothing because it was caught fast. It is documented here in full because the lesson — treat a key like a bank card number — is one worth paying for once, cheaply, early.'));
body.push(p('Gathering the reports also involved friction. One report demanded a phone number before it could be downloaded; this is the ordinary price of "free" industry reports, which are funded by collecting reader contact details. A form field that expected a recognised company name showed a small red warning when an unrecognised one was entered. Neither was a real obstacle, but both slowed the day.'));
body.push(h3('What Day Two produced'));
body.push(p('A funded AI account ready for a later phase, a hard lesson in handling secrets, three substantial research reports, and a short document recording where each report came from. The raw material was now on the shelf.'));

// --- Day 3 ---
body.push(h2('6.3 Day Three — Turning Research into Usable Numbers'));
body.push(p('Three large reports are not, by themselves, usable by a computer. They are hundreds of pages of human prose. Day Three was about extracting from them a small, structured set of benchmark numbers — the figures that would later shape the synthetic data.'));
body.push(h3('What was done'));
body.push(p('A tool was installed to convert the PDF reports into plain searchable text. The three reports together produced over seventeen thousand lines of text — far too much to read end to end. Instead, a search technique was used: scanning all the text for specific keywords such as "return rate," "lead time," and the names of manufacturing regions, then reading only the paragraphs around each match. This is how analysts actually read large reports. One does not read them cover to cover; one mines them for the small fraction of content that answers a specific question.'));
body.push(p('The findings were distilled into a single reference document of benchmark numbers. A deliberate discipline was applied while writing it: every number was labelled as either directly cited to a source, or, where no source gave a figure, clearly marked as an estimate. This honesty matters. If asked later where a number came from, the project can answer truthfully for every one.'));
body.push(h3('Gaps, and the second search'));
body.push(p('The three reports were strong on broad context but silent on several specific figures the project needed — precise return rates by product category, the current capacity of a key manufacturing region, the operating details of the specific brand chosen as a reference case. These missing figures were the "gaps."'));
body.push(p('To close them, a second, more targeted search was carried out across the open web. It succeeded well: it found a specialised industry report, two recent direct-to-consumer retail studies, news coverage of the reference brand’s finances, and the published annual report of a comparable listed company. Most of the gaps were closed with properly cited figures, and the benchmark document was revised twice more. A fuller account of the resources is given in Section 7.'));
body.push(h3('Errors and setbacks'));
body.push(p('The friction on Day Three was small but instructive. An email drafted to a university professor, requesting expert validation of the estimated figures, was first written with a table formatted in a way that does not display correctly in email. A later paste carried hidden styling that made the text appear inside an ugly black box. Both were formatting issues, not content issues, and both were fixed by stripping the formatting and re-pasting plainly. The lesson: text copied between two different programs often carries invisible formatting with it, and the safe habit is to paste without formatting.'));
body.push(h3('What Day Three produced'));
body.push(p('A single, well-organised benchmark document in which the great majority of figures are cited to a named source, the remainder are honestly marked as estimates, and a clear list of remaining open questions is recorded for future follow-up. The research was now in a form a computer could use.'));

// --- Day 4 ---
body.push(h2('6.4 Day Four — Building the Synthetic Dataset'));
body.push(p('With benchmark numbers in hand, Day Four built the actual dataset: five thousand artificial purchase orders whose statistical behaviour matches the researched reality.'));
body.push(h3('What was done'));
body.push(p('First, foundational programming skill was built directly: two structured online courses, in the Python language and in a data-handling library called Pandas, were completed. This was not a detour; it was the difference between copying code and understanding it.'));
body.push(p('Then an isolated working environment was created for the project — a self-contained Python setup, separate from the rest of the computer, so the project’s tools could never conflict with anything else. Two code files were written. The first holds every parameter: the benchmark numbers, translated from the research document into a form code can read. The second holds the logic: it uses those parameters to generate the orders, one at a time, five thousand times. Section 8 explains how this generation logic works.'));
body.push(p('Finally, the generated data was examined visually — a step called exploratory data analysis — by producing a series of charts to confirm that the data behaved as designed.'));
body.push(h3('Refining and tuning: the calibration loop'));
body.push(p('The first version of the dataset was wrong. It reported that 77 percent of all orders were delayed — a figure far higher than any real business would survive. The cause was diagnosed: several risk factors were being multiplied together, and multiplication compounds quickly, so risk was exploding. The settings were softened and the data regenerated. The second version reported 57 percent — better, still too high. A second cause was found: one seasonal effect was being over-applied. It was corrected. The third version reported 31.7 percent delayed and 29.4 percent returned — both squarely inside the realistic range the research predicted.'));
body.push(callout('Why the calibration loop is recorded as a success, not a failure',
  'Three attempts to get the data right is not a sign the work was sloppy. It is the normal, expected rhythm of building any model: make a version, measure how wrong it is, diagnose why, correct, repeat. The first-pass numbers are almost never right. What matters is that each correction was driven by a specific diagnosed cause, not by random guessing. This loop — build, measure, diagnose, correct — is one of the most transferable skills in the whole project.'));
body.push(h3('Errors and setbacks'));
body.push(p('The exploratory analysis was done in a notebook — an interactive document that mixes code and results. Three small problems occurred. The notebook was first created in the wrong folder, so it could not find the data file. After it was moved, the program kept showing the old, broken state because it had not been refreshed. And an empty, mistaken folder was found cluttering the project and was removed. None was serious; all are recorded because together they are a fair picture of what an ordinary working day actually feels like.'));
body.push(h3('A genuine discovery'));
body.push(p('The charts produced one real surprise. It had been assumed that the single manufacturing region known to be under the most strain would clearly have the worst delay rate. The data showed otherwise: a different region matched it almost exactly. The reason, on inspection, was sound — the second region’s combination of less reliable suppliers and a fabric type with longer production times added up to the same total risk. This is exactly the kind of multi-factor interaction a human reasoning about one cause at a time would miss, and a data-driven approach catches. It was the first moment the project taught its author something rather than the reverse.'));
body.push(h3('What Day Four produced'));
body.push(p('A calibrated five-thousand-order dataset whose every distribution traces back to a researched figure, a set of charts confirming it behaves correctly, and a first genuine analytical insight.'));

// --- Day 5 ---
body.push(h2('6.5 Day Five — The Rule-Based Scorer'));
body.push(p('Day Five built the first of the two prediction methods: the transparent, hand-designed rule-based scorer. This was the day the author’s own domain judgment was turned directly into working code.'));
body.push(h3('What was done'));
body.push(p('The work began on paper, not in code. A scoring rubric was designed: a list of risk factors, and for each one, a number of points it should add to an order’s delay score and to its return score. Every order would start from a baseline and accumulate points as risk factors applied. Designing this rubric is the genuine intellectual core of the project, because the weights encode real supply chain knowledge.'));
body.push(p('Once the rubric was agreed, it was translated into code: a function that reads one order and returns its two scores, each accompanied by a written list of the exact reasons behind it. The author wrote a substantial portion of this code directly. The scorer was then run across all five thousand orders, and its scores were checked against what actually happened to those orders.'));
body.push(h3('Refining and tuning: the rubric scale problem'));
body.push(p('The first draft of the rubric had a structural flaw. Every factor had been given a similar weight — all of them clustered between 20 and 36 points. The effect was that a genuinely risky order and an ordinary order received almost the same total score. A scoring system in which everything scores about the same cannot tell anything apart. The fix was to widen the range dramatically: minor factors were dropped to single digits, major factors raised, so the gap between "slightly risky" and "very risky" became large and meaningful. One factor in particular — a brand-new, untested supplier — had been badly underweighted and was raised to become one of the largest weights, matching what the research clearly indicated.'));
body.push(h3('Validation: what the scorer revealed'));
body.push(p('When the finished scorer was checked against reality, it produced one strong result and one weak one, and the contrast became one of the project’s most important findings.'));
body.push(p('The delay scorer was excellent. Orders it rated low-risk were delayed about 9 percent of the time; orders it rated high-risk were delayed about 92 percent of the time. That is a tenfold separation — a scorer that genuinely tells safe orders from dangerous ones.'));
body.push(p('The return scorer was much weaker. Low-rated orders were returned about 22 percent of the time; high-rated orders about 44 percent. A real effect, but only a twofold separation, far softer than the delay result.'));
body.push(callout('The finding: some things are simply harder to predict',
  'The weak return result is not a defect in the rubric. It is a true fact about the problem. A large part of return risk depends on things that cannot be known on the day an order is placed: whether the order will actually end up late, and how the customer will subjectively feel about the fit and fabric when the parcel arrives. No system, however well built, can predict from order-day information something that is partly determined by later, partly random events. Recognising and stating this limit — rather than hiding it — is itself a mark of sound analysis.'));
body.push(h3('What Day Five produced'));
body.push(p('A complete, transparent, fifteen-factor risk scorer; a dataset with every order scored; a documentation file explaining and justifying every weight; and a clear-eyed understanding of which of the two predictions is reliable and which is inherently hard.'));

// --- Day 6 ---
body.push(h2('6.6 Day Six — The Machine Learning Model'));
body.push(p('Day Six built the second prediction method: a machine learning model, which learns risk patterns from the data itself rather than from hand-written rules.'));
body.push(h3('What was done'));
body.push(p('Two specialised software libraries were installed — one a general toolkit for machine learning, the other a specific, powerful algorithm called XGBoost. The data was then prepared for the algorithm. Machine learning algorithms work only with numbers, so text columns such as a region name had to be converted into numeric form, a step called encoding. After encoding, the dataset’s ten columns of information had expanded into twenty-eight numeric columns.'));
body.push(p('The data was then split into two parts: 80 percent for training the model and 20 percent kept hidden, for testing it. This separation is the single most important rule of honest machine learning. A model tested on data it has already studied could simply memorise the answers; only data it has never seen gives an honest measure of real performance.'));
body.push(p('Two models were then trained — one to predict delays, one to predict returns — and each was tested on the hidden data.'));
body.push(h3('Errors and setbacks'));
body.push(p('The XGBoost algorithm refused to run at first. The error message, read carefully, was precise and helpful: it needed a system-level component called OpenMP, which enables a program to use several processor cores at once. The Python part of the library had installed correctly, but it depends on a separate underlying component that the language’s own installer cannot provide. Installing that component through Homebrew fixed it at once. The lesson is a real distinction worth knowing: some software pieces are managed by the language’s installer, and some are managed by the operating system’s installer, and an error about a missing library file usually means the second kind.'));
body.push(h3('The results, and an independent confirmation'));
body.push(p('The delay model performed well. On the hidden test data its overall ranking quality — a standard score where 0.5 is pure guesswork and 1.0 is perfection — was 0.855, comfortably in the range considered good.'));
body.push(p('The return model performed poorly. Its score was 0.578, barely above pure guesswork.'));
body.push(callout('Why a near-failure is one of the project’s best results',
  'On Day Five, the hand-built rule scorer found that delays predict well and returns predict badly. On Day Six, a completely different method — a machine learning algorithm, built on entirely different principles — reached the same conclusion: delays scored 0.855, returns only 0.578. When two independent methods, designed in different ways, agree on a finding, that finding is real and not an artefact of either method. The weak return result is therefore not a failure to be hidden. It is a genuine, twice-confirmed discovery about the problem: order-day information is enough to predict delays and is not enough to predict returns. It also points directly at the purpose of the next phase — returns need a different kind of evidence, namely the customer’s own words, which is exactly what the language-model layer will provide.'));
body.push(h3('Feature importance: what the models leaned on'));
body.push(p('After training, each model was examined to see which pieces of information it had relied on most heavily. The result was itself a discovery. The delay model concentrated its attention sharply: a single piece of information — whether the order fell in an ordinary season — accounted for well over a third of its decision-making, with a small group of others carrying the rest. The return model showed the opposite pattern. Its attention was spread thinly across many pieces of information, with no clear leader, and several details that ought to carry no real meaning ranked surprisingly high. This shape is itself a diagnostic test. Concentrated importance is the fingerprint of a model that has found genuine structure; thinly smeared importance, with meaningless details ranking high, is the fingerprint of a model that has found very little. The delay model had found a real pattern; the return model had not. It was the third independent confirmation, after the rule scorer and the accuracy score, of one consistent finding.'));
body.push(h3('The hybrid, and an honest lesson about blending'));
body.push(p('The final step of Phase 4 was to blend the two methods — the hand-built rule scorer and the machine learning model — into a single combined prediction, the hybrid. The first attempt used a simple equal blend, giving each method half the say. It produced a small but instructive disappointment: for both delay and return, the equal blend scored slightly below the better of the two methods used on its own. The reason is clear in hindsight. The two methods are not equally good at each task — the machine learning model is stronger at predicting delays, and the rule scorer is stronger at predicting returns — and giving equal weight to the weaker method simply dilutes the stronger one.'));
body.push(p('The correction was to weight each blend toward whichever method was stronger for that particular task. The weighted hybrid then matched the best single method almost exactly for both predictions. But the more important conclusion concerned what the hybrid is actually for. Its value was never a higher accuracy score. Its value is two things an accuracy score cannot capture. It always carries the rule scorer’s plain-language reasons, so every prediction can be explained to the person acting on it. And it compares the two methods on every single order, agreeing on roughly 84 percent of them and flagging the remaining 16 percent, where the methods disagree, for a human to examine. That is a genuine, usable working procedure, not a number.'));
body.push(h3('What Day Six produced'));
body.push(p('Two trained machine learning models, each honestly measured; a feature-importance analysis that independently confirmed, for a third time, that delays can be predicted and returns largely cannot; and a performance-weighted hybrid that matches the best single method on accuracy while adding full explainability and a human-review flag. With this, Phase 4 is complete.'));

// --- Day 7 ---
body.push(h2('6.7 Day Seven — The Language-Model Layer'));
body.push(p('Day Seven built the third and final source of insight in the prediction system: the language-model layer. Its purpose had been set by the Phase 4 results. Those results had shown, three separate times, that returns cannot be predicted from order-day information alone. The missing evidence — the reasons a customer actually sends a garment back — does not live in any data column. It lives in what customers themselves write. Day Seven went and read it.'));
body.push(h3('What was done'));
body.push(p('The raw material for this phase is the customer review. The brand chosen as the project’s reference case, a direct-to-consumer menswear company, has a mobile application, and that application carries a public page of customer reviews. A short program was written to collect those reviews automatically — a process called web scraping. It gathered about 1,200 recent reviews, each with its star rating and its written text, and saved them as a data file.'));
body.push(p('These reviews matter for one specific reason: they are real, and they are independent. Every number in the synthetic dataset was shaped by the project’s own research. The reviews were not. They are the unfiltered words of real customers who have never heard of this project. That independence is exactly what allows them to check the model, rather than simply echo it.'));
body.push(p('The star ratings of the collected reviews formed a revealing shape. Rather than clustering around the middle, they piled up at the two extremes — a large group of one-star reviews and a large group of five-star reviews, with relatively little in between. The angriest customers and the happiest customers are the ones who write; the indifferent majority stays silent. The large body of one-star reviews, in particular, was the project’s richest seam of supply chain complaints.'));
body.push(p('Raw review text cannot be analysed directly; it must first be sorted into categories. So before any automation, a classification schema was designed — a fixed, agreed list of the things a review might be about. Six categories were settled on: a delivery delay, a return or refund problem, a sizing or fit problem, a product-quality problem, a customer-service problem, and, for reviews raising none of these, no category at all. The schema was deliberately multi-label, meaning a single review can be tagged with several categories at once, because real complaints often are: "it came late and the size was wrong" is two distinct problems in one sentence.'));
body.push(p('The reading itself was done by a large language model — an artificial-intelligence system, reached through the paid API account opened back on Day Two, that can read ordinary text and judge its meaning. The model was given a careful written instruction, called a prompt. It was told to act as a supply chain analyst, given the precise definition of each of the six categories, and given firm rules: tag only what a review actually says, judge the words and never the star rating, and allow a review to carry more than one tag.'));
body.push(p('The reviews could not sensibly be sent to the model one at a time — that would mean over a thousand separate requests — nor all in a single request. They were sent in batches of twenty, around sixty requests in total: small enough for the model to stay accurate on each review, large enough to keep the number of requests low.'));
body.push(p('One difficulty had to be solved first. A language model, left to itself, replies in ordinary prose, and ordinary prose is unpredictable — it might add a friendly sentence, or format its answer differently each time. But this answer was not going to be read by a human. It was going to be read by other code, and code needs an answer in one exact, unvarying shape. The solution was a feature called structured outputs: the model is handed a strict template describing the precise shape its answer must take, and the service then guarantees the reply matches it. This turns "ask politely and hope" into a guaranteed, machine-readable result.'));
body.push(p('The pipeline was first tested on a small sample of forty reviews — a deliberate habit, to confirm cheaply that it worked before committing to the full run — and then run across the whole set. It classified 1,189 reviews into their supply chain themes, at a total cost of roughly one US dollar of API credit.'));
body.push(h3('Errors and setbacks'));
body.push(p('The phase had its friction. Early on, a command meant to be run in the terminal was copied together with a short written note explaining what it did. The terminal did not treat that note as harmless: it tried to run the explanation as part of the instruction, and rejected the whole line. The cause, once seen, was simple — a command and a sentence describing the command are two different things, and only the command itself should ever be run. Nothing was damaged; the instruction had merely been refused before it could act.'));
body.push(callout('The eleven missing reviews',
  'The full run classified 1,189 reviews — not the 1,200 that were sent. Eleven had quietly gone missing, and the reason is worth understanding. The structured-outputs feature guarantees that every answer the model returns has the correct shape. It does not guarantee that the model returns an answer for every single review in a batch. Across sixty batches, eleven reviews were simply left out. The fix was to make the pipeline resumable: able to be run again, recognise which reviews were already classified, and process only the ones still missing. With that safeguard in place, the project then made a deliberate choice — rather than chase the final eleven, it proceeded with the 1,189. At 99.1 percent coverage, with the omitted reviews scattered at random, the analysis loses nothing real, and an honest footnote about eleven missing reviews is worth more than a hidden imperfection. The lesson is twofold: a guarantee about the shape of an answer is not a guarantee about its completeness; and any long task that costs money, or can fail partway, should be built so it can be safely resumed.'));
body.push(h3('Validation: do real customers agree with the model?'));
body.push(p('The reviews were classified so they could answer one question: does the model’s account of supply chain risk match what real customers actually complain about? Answering it required care, because the synthetic orders and the real reviews cannot be matched one to one — an invented order is not any real customer’s order. The comparison is therefore not a row-by-row check but a triangulation: a test of whether two entirely independent sources tell the same story. If a model built from benchmark-calibrated synthetic data, and the unfiltered voice of 1,189 real customers, point to the same problems, that agreement is strong evidence — precisely because the two sources share no common origin.'));
body.push(p('Four things emerged. First, scope was confirmed: delivery delays and return problems, the two outcomes the model predicts, are both among the most common complaint themes in the reviews. The synthetic data had not been inventing problems that customers do not actually have. Second, return and refund complaints outnumbered delivery-delay complaints by roughly two to one. Returns are not a minor concern but a central one, which justifies the effort spent modelling them even though they are the harder of the two to predict.'));
body.push(p('Third, and most important, the reviews explained the project’s central finding. The model cannot predict returns well because a return is driven by things knowable only after the parcel arrives — whether the garment fits, whether the fabric meets expectations. The reviews named exactly those factors: complaints about sizing and about product quality were present and specific. The order-day data the model sees cannot contain that information, because at the moment an order is placed it does not yet exist. A weak return prediction is therefore not a broken model; it is a model honestly missing information that no order-day system could ever hold.'));
body.push(p('Fourth, an honest gap. The single most common complaint theme was poor customer service — something the model does not predict at all. But a closer look softened this. Of the customer-service complaints, around three in four also mentioned a delivery delay or a return problem. Poor service is, for the most part, not a separate failure but the visible aftermath of the operational failures the model already predicts: an order goes wrong, the customer contacts support, and the support experience compounds the damage. The model addresses the upstream cause, and the loud downstream symptom is largely a consequence of it.'));
body.push(callout('Independent agreement is the opposite of circular reasoning',
  'The fairest criticism of any project built on synthetic data is the charge of circularity: if the data was shaped by the author’s own assumptions, a model trained on it may simply be learning those assumptions back. Phase 5 is the project’s answer to that charge. The customer reviews were written by real people, with no connection to the project and no knowledge of its assumptions. When that fully independent evidence points to the same supply chain problems the model emphasises, the agreement cannot be an echo of the project’s own design. Independent corroboration is, by definition, the opposite of circular reasoning — and providing it was the entire purpose of this phase.'));
body.push(h3('What Day Seven produced'));
body.push(p('A set of 1,189 real customer reviews, each automatically classified into clear supply chain themes; a classification pipeline built to be resumable and honest about its own gaps; and a validation that did exactly what it was designed to do. Using evidence entirely independent of the project, it confirmed that the model is built around the right problems, and it explained, in customers’ own words, why one of the model’s two predictions is inherently the harder one. With this, Phase 5 is complete.'));

// --- Day 8 ---
body.push(h2('6.8 Day Eight — The Output Layer'));
body.push(p('The first seven days built a working prediction system. But a system is not the same thing as a tool. The scorer, the models, and the review analysis all lived in code, runnable only by the person who wrote them. Day Eight — the work of Phase 6 — set out to turn that system into something a real person could pick up and use. It produced two distinct tools, built on purpose for two different kinds of user.'));
body.push(h3('Why two tools, and not one'));
body.push(p('A single dashboard would have been simpler to build. It was not built, because the people who would use ThreadTrack do not all work the same way. A supply chain analyst inside a clothing brand lives, in practice, inside spreadsheets — that is the environment they trust and control. A planning manager, or a hiring manager reviewing this project, wants something they can click through in a browser without installing anything at all. Forcing both kinds of user into one format would have served neither of them well. So the output layer has two front doors: a spreadsheet tool for the people who work in spreadsheets, and an interactive dashboard for everyone else.'));
body.push(h3('The spreadsheet tool'));
body.push(p('The first deliverable is a spreadsheet workbook that reproduces the rule-based scorer entirely inside spreadsheet formulas. This is not a screenshot, and it is not an export of results. It is the scorer itself, rebuilt in the one tool a supply chain analyst already knows. An analyst types the details of a new order into a row, and the workbook computes its delay score, its return score, the risk band for each, and the written list of reasons behind them — using the exact same fifteen-factor logic as the project’s code.'));
body.push(p('The workbook has four sheets. A "Read me" sheet explains, in plain terms, what the tool does and how to use it. An "Order book" sheet is the working surface, where orders are entered and scored, with the risk bands colour-coded so the dangerous orders stand out at a glance. A "Summary" sheet rolls the order book up into totals. A "Rubric" sheet lists every one of the fifteen factors and its exact point weights, so the analyst can see precisely why the tool scores the way it does — the same transparency principle that governs the whole project.'));
body.push(p('Two spreadsheet features do quiet but important work. Conditional formatting is a rule that paints a cell a colour based on its value; here it turns a high-risk score red without anyone colouring it by hand. Data validation is a rule that restricts what a cell will accept; here it forces the fabric, payment, and season fields to be chosen from fixed lists, so a typo cannot silently break a formula. Together they make the workbook hard to use wrongly.'));
body.push(h3('The interactive dashboard'));
body.push(p('The second deliverable is a web dashboard: a single application, organised into four tabs, that anyone can open in a browser. The first tab, the Order book, shows every scored order in a filterable, sortable, colour-coded table, with a panel to inspect any single order in full. The second tab, Score a new order, is a live form: a user enters the details of an order they are about to place and receives its risk assessment at once. The third tab, the Portfolio view, rolls the whole order book up into the totals and charts a manager would want — how many orders are high-risk, and how risk varies by manufacturing region and by season. The fourth tab, How it works, explains the model and shows the Phase 5 validation in plain language.'));
body.push(p('The dashboard was shaped by one consistent principle: a user should be asked only for things they actually know, and never made to do the system’s reasoning on its behalf. Three design decisions followed directly from that principle.'));
body.push(p([b('The user enters a city, not a tier. '), t('Delivery distance in the model is captured by a city’s "tier" — a three-level grading of how far and how difficult a place is to deliver to. But the person placing an order knows the city; they should not be asked to know its tier. So the dashboard carries a built-in classification of roughly one hundred and sixty Indian cities, and derives the tier itself the moment a city is chosen.')]));
body.push(p([b('The user picks a vendor, not a set of vendor statistics. '), t('Each supplier carries several attributes the scorer needs — its manufacturing region, its reliability, whether it is still unproven. A user should not be typing reliability figures by hand. They choose a vendor from a list, and every attribute is looked up automatically. A first-time vendor can be added on the spot; once an order with it is confirmed, it joins the list for next time.')]));
body.push(p([b('The user enters an order date, not a season. '), t('The season an order falls into changes its risk — but "season" is not a fact a user should have to judge, and it is not even uniform across the country. The Indian monsoon reaches the four manufacturing regions on different timelines. So the dashboard holds a small region-aware calendar: the user enters the date the order is placed, and the season — normal, monsoon, or festive — is worked out from that date together with the supplier’s region. The same date can be monsoon for one region and an ordinary month for another, and the calendar reflects that.')]));
body.push(p('A fourth decision concerned what happens after an order is scored. The dashboard does not simply file the new order away. It shows the score first, and then asks the user to confirm the order or discard it. This is deliberate. The tool exists to support a decision — whether to place this order at all — and the score is meant to inform that decision, not to make it. The human makes the call; the tool only makes the call better informed. This is the same "an assistant, not a replacement" principle stated back in Section 3, now built directly into the shape of the screen.'));
body.push(h3('Errors and setbacks'));
body.push(callout('The #NAME? error: Excel’s hidden function names',
  'When the workbook was first generated, one column — the written list of risk reasons — showed the error "#NAME?" in every row instead of any text. "#NAME?" is Excel’s way of saying it does not recognise a name used in a formula. The cause was specific and instructive. The formula used a function called TEXTJOIN, a relatively modern addition to Excel. For backward compatibility, a program that writes a spreadsheet file directly must refer to these newer functions by a special internal name, prefixed with "_xlfn." A formula written as plain "TEXTJOIN" is understood when a human types it, but must be written as "_xlfn.TEXTJOIN" when a program writes the file. Adding the prefix fixed every row at once. The lesson: a file written by a program is not always identical to the same file typed by a person, and the difference is exactly where this kind of bug hides.'));
body.push(callout('The KeyError: state that outlived the code',
  'While the dashboard was being built, it began to show a red error wall: a "KeyError," which means the program asked for a stored piece of information that was not there. The cause was subtle. The dashboard keeps a small memory of the current session — the last order the user scored, and so on. During development the code is edited constantly, and the page reloads itself each time it is saved; but the session memory survives those reloads. An order scored by an older version of the code had left behind a memory in a shape the newer code no longer expected, and the newer code, reaching for a piece the old shape did not contain, failed. The fix was to store all the related pieces of that memory as a single unit, so it can never again exist in a half-updated shape. The lesson is general, and applies to any program that remembers things while its own code changes: stored state can outlive the code that created it, and code must be written to survive that.'));
body.push(h3('What Day Eight produced, and what remains'));
body.push(p('Day Eight produced the two tools that make ThreadTrack usable by someone other than its author: a spreadsheet workbook that rebuilds the scorer inside the analyst’s own environment, and a four-tab interactive dashboard built around the principle of asking the user only what they genuinely know. Both are working, and both are committed to the project repository.'));
body.push(p('Phase 6 is not yet finished. Two pieces of the output layer remain. The first is putting the dashboard online at a public web address, so it can be opened by anyone with the link, with no installation at all. The second is the written case study — a single document that ties the whole six-phase project together for a reader deciding whether to hire its author, and that sets out what a real production deployment of ThreadTrack would require beyond this portfolio version. The next update to this document will record both, and will mark Phase 6, and the project, complete.'));
body.push(pageBreak());

// ===== SECTION 7 =====
body.push(h1('7. The Resources: What We Used and Why'));
body.push(h2('7.1 The four-archetype framework'));
body.push(p('Research resources were not gathered at random. They were chosen to fill four distinct roles, because each kind of source is strong where the others are weak. Using all four together allows the figures from each to be cross-checked against the others — a practice called triangulation.'));
body.push(spacer());
body.push(table(
  ['Archetype', 'What it provides', 'Why it matters'],
  [
    ['Global consultancy report', 'Worldwide industry trends and the direction of travel', 'Establishes the big-picture context'],
    ['National industry report', 'Country-specific market structure and economics', 'Connects global trends to the actual local market'],
    ['Government data', 'Official, indisputable production and trade figures', 'Provides a credibility anchor no one can dispute'],
    ['Listed-company filing', 'Real operating data from a comparable real business', 'Replaces estimates with cited real-world numbers'],
  ],
  [2300, 3700, 3360]
));
body.push(h2('7.2 The specific sources used'));
body.push(p('Three primary reports were collected first: a global fashion-industry report (the consultancy archetype), a study of India’s direct-to-consumer retail sector (the national archetype), and the Ministry of Textiles annual report (the government archetype). The second search added a specialised national industry report, two further retail-sector studies, the annual report of a comparable listed clothing company (the company-filing archetype), and several pieces of recent news coverage and industry reference material.'));
body.push(h2('7.3 The gaps, and the second search'));
body.push(p('As Section 6 recorded, the first three reports left specific gaps: category-level return rates, current manufacturing-region capacity, and the reference brand’s operating details were all missing. The disciplined response was not to invent these numbers but to search specifically for them, and to clearly mark any that still could not be found as estimates. This is the difference between a project that looks complete and one that is honestly complete.'));
body.push(pageBreak());

// ===== SECTION 8 =====
body.push(h1('8. The Code: What Each File Does'));
body.push(p('This section explains the project’s main code files in plain terms. The aim is not to teach programming but to make clear what each file is responsible for.'));
body.push(spacer());
body.push(table(
  ['File', 'Responsibility'],
  [
    ['config (parameters)', 'Holds every benchmark number in a form code can read. Separated from the logic so a number can be changed without touching any working code.'],
    ['data generator', 'Uses the parameters to create the 5,000 synthetic orders, one at a time, and saves them as a data file.'],
    ['rule scorer', 'Reads one order and returns its delay score, return score, and the written list of reasons behind each.'],
    ['scorer application', 'Runs the rule scorer across the whole dataset and checks its scores against what actually happened.'],
    ['model notebook', 'Trains, tests, and evaluates the two machine learning models.'],
    ['review scraper', 'Collects about 1,200 real customer reviews from the brand’s app store page and saves them as a data file.'],
    ['review classifier', 'Sends the reviews to a language model in batches and tags each one with its supply chain themes.'],
    ['validation script', 'Compares the review themes against the model’s findings and produces the Phase 5 validation charts.'],
    ['workbook builder', 'Generates the spreadsheet risk tool — rebuilding the fifteen-factor scorer in Excel formulas across four sheets, with colour-coding and input validation.'],
    ['dashboard', 'The four-tab web application: the order book, the live scoring form, the portfolio roll-up, and the explanation of the model.'],
  ],
  [2500, 6860]
));
body.push(h2('8.1 The one idea behind the data generator'));
body.push(p('The generator works on a single principle that is worth stating plainly: the benchmark numbers define the shape of reality, and the code rolls dice that are loaded to match that shape. A fair die gives every outcome an equal chance; a loaded die favours some outcomes. The benchmark figures decide how each die is loaded. To create one order, the code rolls a loaded die for the supplier, another for the fabric, another for the destination, and so on. To decide whether that order is delayed or returned, it calculates a probability from the benchmark figures and then, in effect, flips a coin weighted by that probability. Repeated five thousand times, this produces a dataset that is artificial in origin but realistic in its statistical shape.'));
body.push(h2('8.2 The principle of separating parameters from logic'));
body.push(p('The numbers and the logic were deliberately kept in separate files. The reason is practical. When a benchmark figure needs to change — for instance, when the professor returns the requested expert validation — only the parameter file is edited. The logic is never touched, so it cannot be accidentally broken. This separation is a standard professional practice and it made the calibration loop of Day Four fast and safe.'));
body.push(pageBreak());

// ===== SECTION 9 =====
body.push(h1('9. Honest Reflections: Errors, Setbacks, and Lessons'));
body.push(p('This section gathers, in one place, the difficulties already described in the daily log. They are collected here so the lessons are not lost among the narrative. Every one of them is ordinary. Together they are an accurate portrait of what learning to build something real actually involves.'));
body.push(spacer());
body.push(table(
  ['Setback', 'The lesson it taught'],
  [
    ['The Homebrew installer wall of text', 'A wall of text is usually information, not an error. Real errors name themselves.'],
    ['A command typed in the wrong window', 'A command only works in the program it belongs to. Know which window you are in.'],
    ['The "gitgit" typo; saving from the wrong folder', 'Small, fast-to-fix friction is normal. Check where you are before acting.'],
    ['The payment form would not work', 'When an online form misbehaves for no clear reason, suspect the browser itself.'],
    ['An API key pasted into a chat', 'Treat a secret key like a bank card number. If exposed, revoke it immediately.'],
    ['The first dataset was 77 percent delayed', 'First-pass model output is almost never right. Build, measure, diagnose, correct, repeat.'],
    ['The rubric scale problem', 'A scoring system where everything scores alike cannot tell anything apart. Spread the weights.'],
    ['XGBoost would not run', 'Some components come from the language installer, some from the system installer. Read the error.'],
    ['The return models scored poorly', 'Not every problem is solvable with the data at hand. Saying so honestly is good analysis.'],
    ['A command pasted with its comment', 'A command and a sentence describing it are two different things. Run only the command.'],
    ['Eleven reviews silently omitted', 'A guarantee about an answer’s shape is not a guarantee it covers every input. Build long jobs to be resumable.'],
  ],
  [3900, 5460]
));
body.push(spacer());
body.push(p('A single theme runs through the list. Almost none of these were failures of intelligence. They were failures of unfamiliarity — the ordinary cost of doing something for the first time. Each was resolved, each taught something durable, and none of them stopped the project. That is the honest, raw shape of real work, and it is recorded here on purpose.'));
body.push(pageBreak());

// ===== SECTION 10 =====
body.push(h1('10. Where We Are Now, and What Comes Next'));
body.push(p('At the time this document was last updated, Phases 1 through 5 are complete, and Phase 6 is well under way. The project has: a fully set-up development environment and code repository; a researched benchmark document with most figures cited; a calibrated five-thousand-order synthetic dataset; an exploratory analysis confirming the data behaves correctly; a transparent fifteen-factor rule-based scorer with strong delay performance; two trained machine learning models, with the delay model performing well and the return model honestly reported as weak; a performance-weighted hybrid that combines the two; and a language-model layer that classified 1,189 real customer reviews and used them to validate the whole model against independent real-world evidence.'));
body.push(p('Phase 6, the final phase, turns that working system into finished, usable tools. Two of its three deliverables are now built and committed: a spreadsheet-based risk tool of the kind supply chain analysts use daily, and a four-tab interactive dashboard that runs in a web browser. Two tasks remain before the project is complete: putting the dashboard online at a public web address, and writing the case study that ties the whole project together and sets out what a real production deployment would require.'));
body.push(p('One external thread remains open: a request to a university professor for expert validation of the project’s estimated supply chain lead-time figures. Because the parameters are kept separate from the logic, those figures can be updated the moment a reply arrives, with no disruption to the rest of the system.'));
body.push(callout('A note on this document',
  'This is a living document. It is updated at the end of each work session, so that it always reflects the true current state of the project. The next update will record the completion of Phase 6 — the dashboard online at a public address, and the case study written — and with it the completion of the project.'));
body.push(pageBreak());

// ===== SECTION 11 — GLOSSARY =====
body.push(h1('11. Glossary'));
body.push(p('Every specialised term used in this document, defined in plain language.'));
body.push(spacer());
body.push(table(
  ['Term', 'Plain-language definition'],
  [
    ['Supply chain', 'The complete journey of a product from raw material to the customer.'],
    ['Purchase order', 'A single, specific order placed with a supplier to make a quantity of goods.'],
    ['Delay', 'A product arriving later than it was promised to arrive.'],
    ['Return', 'A delivered product that the customer sends back.'],
    ['Synthetic data', 'Data generated artificially, here shaped to match real cited industry figures.'],
    ['Calibration', 'Adjusting a model’s settings until its output matches a known real-world target.'],
    ['Benchmark', 'A reference figure drawn from research, used to set or check a model.'],
    ['Repository (repo)', 'A project folder whose entire history of changes is tracked and recoverable.'],
    ['Commit', 'A permanently saved snapshot of the project at one point in time.'],
    ['API', 'A service window through which one program sends requests to another.'],
    ['API key', 'A long secret password that grants, and bills, access to an API service.'],
    ['Rule-based scorer', 'A prediction method built from transparent, hand-written rules.'],
    ['Machine learning', 'A method in which an algorithm learns patterns from data on its own.'],
    ['XGBoost', 'A specific, powerful machine learning algorithm used in this project.'],
    ['Encoding', 'Converting text information into the numeric form an algorithm requires.'],
    ['Train/test split', 'Reserving part of the data, unseen, to honestly measure a model.'],
    ['ROC-AUC', 'A score of ranking quality: 0.5 is guesswork, 1.0 is perfection.'],
    ['Leakage', 'The error of letting a model use information it could not really have in advance.'],
    ['Exploratory data analysis', 'Examining data with charts and summaries to understand and check it.'],
    ['Hybrid score', 'A single prediction formed by blending the rule-based and machine-learning results.'],
    ['Web scraping', 'Collecting information from a website automatically with a small program.'],
    ['Large language model', 'An artificial-intelligence system that reads ordinary text and judges its meaning.'],
    ['Prompt', 'The written instruction given to a language model that tells it what to do.'],
    ['Structured outputs', 'A feature that forces a language model’s reply into a fixed, machine-readable shape.'],
    ['Multi-label classification', 'Sorting items into categories where one item may belong to several at once.'],
    ['Triangulation', 'Checking a finding by testing whether independent sources agree on it.'],
    ['Dashboard', 'An interactive screen that presents data and tools in a browser, organised for quick use.'],
    ['Conditional formatting', 'A spreadsheet rule that changes a cell’s appearance automatically, based on its value.'],
    ['Data validation', 'A spreadsheet rule that restricts a cell to accept only values from a fixed, allowed set.'],
  ],
  [2400, 6960]
));

// ---------- assemble ----------
const doc = new Document({
  creator: 'Anusha Chakraborty',
  title: 'ThreadTrack — Process Documentation',
  styles: {
    default: { document: { run: { font: 'Calibri', size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 32, bold: true, color: '2E5B8A', font: 'Calibri' },
        paragraph: { spacing: { before: 320, after: 200 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 26, bold: true, color: '3A3A3A', font: 'Calibri' },
        paragraph: { spacing: { before: 260, after: 140 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 23, bold: true, color: '2E5B8A', font: 'Calibri' },
        paragraph: { spacing: { before: 180, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: 'bullets',
        levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 460, hanging: 280 } } } }] },
    ],
  },
  features: { updateFields: true },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    footers: {
      default: new Footer({ children: [ new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [ new TextRun({ text: 'ThreadTrack Process Documentation   |   Page ', size: 18, color: '888888' }),
          new TextRun({ children: [PageNumber.CURRENT], size: 18, color: '888888' }) ],
      }) ] }),
    },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(__dirname + '/../ThreadTrack_Process_Documentation.docx', buf);
  console.log('Document written: docs/ThreadTrack_Process_Documentation.docx');
});
