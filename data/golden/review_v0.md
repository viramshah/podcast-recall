# Golden set v0: review sheet (generated)

Regenerate with the script that wrote it, or read any item with `uv run podcast-recall eval show <id>`.

## How to review (about 3 hours)

For each question, decide: **keep**, **edit** or **replace**. Check four things:

1. **Would you really ask this?** Natural wording, not copied from the transcript. If not, rewrite it in your words.

2. **Is the gold answer right and complete?** Read the transcript text under it (and open the link if unsure). Fix the gold answer, or the time, in `data/golden/golden_v0.csv`.

3. **Is the time inside the answer?** The link opens at the gold time. For a who/when question, the answer must be at that time.

4. **For the unanswerable, false-premise and not-in-library types:** is the answer truly absent from the library (or present only in a held-out episode)? `eval check` searches for the phrases listed.

**Your own questions:** at least a third of the final set (20 of 60) should be ones you write from memory. Replace a drafted question of the same type with yours, set `author` to `pm`, and keep the type counts (20 / 13 / 10 / 7 / 5 / 5). Questions you author from episodes in the library need `gold_evidence` as `video_id@mm:ss`.

Split: **dev** items may be used for tuning later; **heldout** items are only for the final gate. Don't use heldout items to tune anything.


## Single-fact lookup (20)

### sf01: What can push inflation away from a central bank's target, according to the guest?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** A surge in demand in the economy (for example from a large inflow of foreign money), or government programmes that add to demand.
- Key points: demand boom; foreign money inflows; government programmes
- Evidence: [Ex-IMF Chief Economist: How USA Debt Triggers a Global Crisi at 10:30](https://youtu.be/dNIef2fGLQY?t=630)
  > is, what can generate inflation deviating from target? It could be that there is so much of a boom in demand in the economy now for multiple reasons, including, say, you're getting a lot of infusion of foreign money, multiple reasons for it. There's a big increase in demand or the government, which is very

### sf02: What was the IMF originally created to be, and what test decides whether it lends to a country?
- Split: heldout `raj`  |  Author: claude
- **Gold answer:** It was created to be a financial firefighter. It lends if it has confidence that the country's new government will move the country away from the abyss.
- Key points: financial firefighter; confidence in policies
- Evidence: [Ex-IMF Chief Economist: How USA Debt Triggers a Global Crisi at 1:10:51](https://youtu.be/dNIef2fGLQY?t=4251)
  > The decision about whether you lend to a country or not is whether you have confidence that the policies that this new government, by the way, whoever is going to be in power, will be able to move the country away from the abbess. That's always the test. Nobody ever has defaulted to the IMF,

### sf03: Which questions does the guest suggest putting to an AI assistant to find channel partners for a product?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** Which markets the product is used in, who the customers are, and through which channels they get access to such services; then ask for a profile of 10 to 20 companies.
- Key points: markets; customers; channels; profile 10-20 companies
- Evidence: [Billion-Dollar Tech CEO: How To Make AI Work Like 100 Employ at 1:06:36](https://youtu.be/8ol3j7o1U7o?t=3996)
  > what are the top markets in which this product has been used? Who are the customers who are using this? Okay. What are the different channels through which they are getting access to these services? Give me the names of, build me a full profile of 10, 20 people, companies in each of those markets

### sf04: What does the guest say about small businesses and the five-year mark?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** Around half of small businesses do not survive five years, so you must understand your unit economics, entry cost and payback period, not only sales.
- Key points: 50% fail by five years; unit economics; payback period
- Evidence: [Billion-Dollar Tech CEO: How To Make AI Work Like 100 Employ at 1:23:16](https://youtu.be/8ol3j7o1U7o?t=4996)
  > Remember that 50% of the cost SMBs don't survive the five-year curve. How do you make sure that, yes, it is good you're selling, but are you making money? Do you understand your unit economics, your entry cost, your payback period? LTV to CAC, I'm refraining from it right now because we are starting new,

### sf05: What does Vinh Giang give as the first step to communicating better?
- Split: heldout `raj`  |  Author: claude
- **Gold answer:** Become self-aware: you have never seen yourself communicate, and your view of how you come across is not accurate.
- Key points: self-awareness; your view is not accurate
- Evidence: [Why Your Communication Makes People Ignore You & How To Fix  at 14:40](https://youtu.be/BgeNDG5jD60?t=880)
  > I would say the first thing is let's become self-aware. All right. You've never seen yourself communicate to somebody else. You have a view of how you think you communicate. It's not accurate, right? Unless you're a content creator, unless you're watching your videos back, unless you do podcasts all the time, which most people

### sf06: When does he say you should write down a story you might tell later?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** Whenever something emotionally moves you, grab your phone and document it straight away; the biggest rule of storytelling is to document.
- Key points: document when emotionally moved; use your phone
- Evidence: [Why Your Communication Makes People Ignore You & How To Fix  at 1:11:39](https://youtu.be/BgeNDG5jD60?t=4299)
  > do you document? Document when something emotionally moves you. anytime something emotionally moves you document it from this point in life right now where you are in life the moment you feel a strong emotion with something something that happened to you during that day or that week grab your phone out document it and

### sf07: Where does Josh Woodward say the best new product ideas at Labs actually come from?
- Split: dev  |  Author: claude
- **Gold answer:** Rarely from design sprints or scheduled idea sessions. They come when people are hacking and building on their own, in the hallway, on weekends or over a break, and then share a video.
- Key points: not design sprints; hacking on weekends and breaks
- Evidence: [Why every company now needs to think and operate like a lab  at 6:19](https://youtu.be/3I6QYkccd3o?t=379)
  > They very rarely, at least in my experience, have come from design sprints or times where you set aside on a calendar, okay, this is, we're going to go come up with our next idea. They usually come When people are swimming in the hallway, maybe on a weekend, often over a break, a lot

### sf08: What happened when the team saw early data on a Gemini feature they had been excited about?
- Split: heldout  |  Author: claude
- **Gold answer:** People looked users in the eye and it wasn't working, and a PM on the team said she didn't think they should launch it. He was proud of her for saying so.
- Key points: early data weak; PM spoke up; did not launch
- Evidence: [Why every company now needs to think and operate like a lab  at 19:00](https://youtu.be/3I6QYkccd3o?t=1140)
  > and we got some of the early data back. People went out, looked in the eyes and it just wasn't there. And so I was so proud of the PM on the team because she was like, I don't think we should launch this. It's not good. And so I replied all is like, this

### sf09: How often does the guest tell a prospect that the gap between them is simply too big?
- Split: dev  |  Author: claude
- **Gold answer:** About one in every four calls. In two to three of every four there is something real.
- Key points: one in four calls; revisit in a year
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 25:44](https://youtu.be/YS9In813jJ0?t=1544)
  > Yeah, there's something real. One out of every four calls, I'm like, listen, based off of the maturity of where you guys are and where we are, it's too much of a gap. Like, I'd love to revisit this in a year, like once you guys have a chance to like solve for X, Y,

### sf10: How should a software price relate to the length of the sales cycle, in the guest's view?
- Split: dev  |  Author: claude
- **Gold answer:** Price should be based on the sales cycle: if you can close in 90 days for 100K, do that every time; a deal that takes nine months should be priced higher.
- Key points: price follows sales cycle; 90 days for 100K
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 59:37](https://youtu.be/YS9In813jJ0?t=3577)
  > Your price should be predicated on your sales cycle, right? Like if you can get a deal done in 90 days for 100K, do that all the time, right? If it takes nine months to get a deal done, you probably should be charging 250, 300K. What are your thoughts on forward deployed engineers as

### sf11: What should you do when the customer's lawyers return extensive redlines on the contract?
- Split: heldout  |  Author: claude
- **Gold answer:** Accept the easy changes, and try to get legal on a live call to talk through the rest, which speeds up the sales cycle.
- Key points: accept easy items; get legal on a call
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 1:14:53](https://youtu.be/YS9In813jJ0?t=4493)
  > No question. If the red lines are extensive, okay, go ahead and accept the things that are easy. The red lines are extensive. See if you can get legal on a call live and just talk through them. That will accelerate your sales cycle. Versus a bunch of back and forth emails. Versus a bunch

### sf12: What does Rob Snyder mean by a hair-on-fire problem?
- Split: dev  |  Author: claude
- **Gold answer:** An urgent, concretely defined problem, such as a to-do that your boss is waiting for and that must happen now.
- Key points: urgent; concrete; must happen now
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 8:43](https://youtu.be/19qrLchbQEc?t=523)
  > And this is an urgent problem. So in a sense, this is the hair on fire problem, very concretely defined. Here's what hair on fire looks like. I have like a to-do my boss is waiting for me to do, and it needs to happen now. It's not just like a general thing that I

### sf13: What kind of reaction from a prospect shows genuine interest, and what shows only polite interest?
- Split: heldout  |  Author: claude
- **Gold answer:** Leaning in ('wait, you can do what?' or 'I will pay you right now') is the signal. Leaned-out enthusiasm ('tell me more', 'send some information for the team to review') is not worth chasing.
- Key points: leaning in vs leaned out
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 25:51](https://youtu.be/19qrLchbQEc?t=1551)
  > What you're looking for as well as they're leaning in. Wait a second, you can do what? What you're not looking for is kind of like leaned out enthusiasm. Okay. Well, tell me more. Well, let me, yeah, we'll, we'll think about it. Can you send more information so our team can review that? Like,

### sf14: What is an agent harness, as explained in the course?
- Split: dev  |  Author: claude
- **Gold answer:** The platform that runs the loop: a model that keeps going until the task is done, connected to your tools and your context. Popular agent products are agent harnesses.
- Key points: loop until done; tools and context; popular agents are harnesses
- Evidence: [AI Agents Full Course 59 Minutes (for beginners) at 6:21](https://youtu.be/eA9Zf2-qYYM?t=381)
  > facilitates this process and basically facilitates this loop to happen is known as an agent harness. And all of the popular AI agent platforms on the market that you'd be familiar with are just agent harnesses. They're just applications where this loop is facilitated. And I want to actually run this little prompt I prepared

### sf15: How is a skill different from keeping something in an agent's memory?
- Split: dev  |  Author: claude
- **Gold answer:** A skill packages a whole process as a markdown file (for example writing a proposal) so it is done the same way each time; memory holds preferences and facts. Process material clogs memory and belongs in skills.
- Key points: skill = packaged process; memory = preferences
- Evidence: [AI Agents Full Course 59 Minutes (for beginners) at 41:25](https://youtu.be/eA9Zf2-qYYM?t=2485)
  > basically it packages up that process into a dot skill file and in that dot skill file it's basically just a marked down file that explains the exact process that you went through so you could create a proposal skill and then every time you now you need a proposal written it just takes that

### sf16: What does the speaker say happens to the work that UGC creators, video editors and motion designers used to do for ads?
- Split: heldout  |  Author: claude
- **Gold answer:** That work is now handled by an AI agent tool; marketing is becoming code, software and tokens.
- Key points: agents replace creator, editor, motion designer; marketing is code
- Evidence: [AI Agents are too good at marketing now at 5:46](https://youtu.be/uJuxenfe-NU?t=346)
  > That whole thing is just stacked. That work is now handled by a GrokBot or a ClogCode or a Dots or whatever it is that you're using. There's, you know, all these different vehicles for this coming out. But I think the big thing I want you to understand is that that labor that was

### sf17: How does the guest connect his bot to Claude Code?
- Split: dev  |  Author: claude
- **Gold answer:** Easy way: tell the bot to log into Claude Code on its own computer. His way: a network of machines connected through Tailscale, using T3 Code.
- Key points: bot logs in itself; Tailscale network; T3 Code
- Evidence: [I'm Obsessed With Grok Bot. Here's Why at 14:51](https://youtu.be/1cWZ7Ekff6E?t=891)
  > How have I connected GrokBot to CloudCode? There's two easy ways to do it. There's two ways to do it. The easy way and the way I've done it. The easy way is every bot has a computer, right? So you can literally tell it, hey, log into CloudCode on your computer and it can

### sf18: What did the guest's bot do when he bought a PS5 Pro?
- Split: dev  |  Author: claude
- **Gold answer:** It emailed the eBay seller, negotiated for him and checked that the console was viable.
- Key points: emailed seller; negotiated; checked viability
- Evidence: [I'm Obsessed With Grok Bot. Here's Why at 43:26](https://youtu.be/1cWZ7Ekff6E?t=2606)
  > Greg? It was my GrokBot. GrokBot emailed the person who listed it on eBay, found out that it was a store in Ontario two hours away, gave me the number, gave me the script to talk to the person. Obviously, I didn't use the script. Called the person, confirmed. I gave it access. It bought

### sf19: Why does the guest's company rely mostly on prompts rather than fine-tuning?
- Split: heldout  |  Author: claude
- **Gold answer:** Because prompting is easy and portable; about 98% of their value comes from prompts.
- Key points: prompts easy; portable; 98%
- Evidence: [Stop building AI wrappers. Start building agent harnesses. at 25:05](https://youtu.be/st61aKW8P5A?t=1505)
  > You have a strong opinion there. Yeah, I think for us, it's 98% prompts is where we get the value out of. Because prompting is easy and it's portable. So like, and by the way, nobody's writing prompts by hand anymore. Like Claude's writing your prompt for you. And so it's really easy. And so

### sf20: What does the host say is ending in software?
- Split: dev  |  Author: claude
- **Gold answer:** The era of dumb tools and dumb SaaS, where a human goes and presses buttons and uploads data to a CRM.
- Key points: dumb SaaS ending; software is evolving
- Evidence: [The $1M+ Solo Grok Bot Business (Full Course) at 5:40](https://youtu.be/67BmkptgTms?t=340)
  > But I think that what's happening is the era of dumb tools, dumb SaaS, where it's like you have a human going and pressing buttons and uploading to a CRM, that is ending. I think we're moving more towards The price for software is trending towards zero and you're going to give away the software


## Cross-episode synthesis (13)

### sy01: What do the guests say about working closely with early customers, even by hand, before trying to scale?
- Split: dev  |  Author: claude
- **Gold answer:** Rob Snyder says starting as a service, with humans doing the work by hand and automation built up around it, can work, though you can get stuck as a services business. The speaker in 'The $1M+ Solo Grok Bot Business' says not to scale right away: sit down with one first client, study their business and watch them.
- Key points: start by hand; one first client; do not scale too early
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 59:53](https://youtu.be/19qrLchbQEc?t=3593)
  > while delivering it a mix of manually and automated. Okay, that's really interesting. That's come up a lot on the podcast, especially with go-to-market sales conversations, this idea of services being a great place to start, which historically has been a terrible idea because the fear is you never actually get to a place where
- Evidence: [The $1M+ Solo Grok Bot Business (Full Course) at 44:10](https://youtu.be/67BmkptgTms?t=2650)
  > Don't try and scale right away. Sit down with that one first client. Try really to solve their business, watch them, shadow them, ask them to like share their screen and go through a process of like something that they do manually, like creating an invoice or, you know, creating products into a presentation and

### sy02: What do the guests say about using content to get a product noticed?
- Split: heldout `raj`  |  Author: claude
- **Gold answer:** Sachin Puri suggests a small business build content around real success stories of founders, and says AI can now produce that content. The speaker in the $1M solo business episode says to make content about your product because people will eventually try it once they have seen you enough.
- Key points: success-story content; AI can make it; keep making content
- Evidence: [Billion-Dollar Tech CEO: How To Make AI Work Like 100 Employ at 47:18](https://youtu.be/8ol3j7o1U7o?t=2838)
  > on SEO as well but somebody who's starting as a small business build a content around that. This is what this interviewer said. This is what they were trying to figure out. Here is a person who actually started from nothing and they became so successful by figuring how to rise against all odds, never
- Evidence: [The $1M+ Solo Grok Bot Business (Full Course) at 20:48](https://youtu.be/67BmkptgTms?t=1248)
  > So yeah, if you guys aren't making content yet for your product, do it because eventually people will see you enough when you make so much content that they'll try your thing. That's how I try T3. And I actually, so my take on it is it's very good. It's very simple. And you can

### sy03: What examples do the guests give of agents repeatedly checking for things on their own?
- Split: dev  |  Author: claude
- **Gold answer:** In the AI Agents Full Course, the presenter has an agent scrape car marketplaces every few hours and notify him when a matching car appears, and describes scheduled tasks such as a morning briefing. In the Grok Bot episode the guest has his bot look through eBay every day for sealed GPU listings.
- Key points: car marketplaces every three hours; morning briefing; eBay listings every day
- Evidence: [AI Agents Full Course 59 Minutes (for beginners) at 52:17](https://youtu.be/eA9Zf2-qYYM?t=3137)
  > you know every three hours I I'm scraping all the different car marketplaces and then I'm getting a notification that you know when something comes up and it's it's crazy right like it saves me I'm one of those people that like if I didn't have this I would be spending an hour of my
- Evidence: [I'm Obsessed With Grok Bot. Here's Why at 42:58](https://youtu.be/1cWZ7Ekff6E?t=2578)
  > And it will like scour through eBay where it will look for listings where people are selling GPUs where the boxes are sealed. Right. So I'm getting like I'm getting listings every single day. And I'll actually share the crazy story. I have a PS5 Pro that I bought recently because I want to play

### sy04: How do the guests say AI is changing marketing and creative work?
- Split: dev  |  Author: claude
- **Gold answer:** In 'AI Agents are too good at marketing now', the speaker says marketing is now just code, software and tokens, and the work of UGC creators, editors and motion designers is handled by bots. In the AI wrappers episode the guest says a top 1% marketing engineer covers SEO, GEO, social and paid ads and has an unfair advantage, while the other 98% risk becoming dinosaurs.
- Key points: marketing is code; creators replaced by bots; top 1% marketing engineer
- Evidence: [AI Agents are too good at marketing now at 5:18](https://youtu.be/uJuxenfe-NU?t=318)
  > Like all marketing is now just code. It's just software and tokens. And so when you look at, you know, an it static image for ads that you generate, when you look at... you know, a C dance video that you create where before I used to hire, have to hire like an avatar, you're
- Evidence: [Stop building AI wrappers. Start building agent harnesses. at 33:35](https://youtu.be/st61aKW8P5A?t=2015)
  > Going back to marketing engineering, in your mind, what does a top 1% marketing engineer look like? Um, well, one thing that comes to mind is they're really a marketing engineer data scientist. So they are like ultra data driven and grounded in what's performing. And this is something that's gotten easier than ever, like

### sy05: What do the guests say about the human abilities that matter as AI takes over routine work?
- Split: heldout `raj`  |  Author: claude
- **Gold answer:** Josh Woodward looks for people with a high unlearning rate, who can learn something and then walk away from it, as well as learning rate and endurance. Sachin Puri says routine data analysis will shrink and people will move to higher-order understanding of the questions to ask. Gita Gopinath tells students not to skip working with classmates now that a brilliant classmate sits on their phone.
- Key points: unlearning rate; higher-order questions; keep working with people
- Evidence: [Why every company now needs to think and operate like a lab  at 32:18](https://youtu.be/3I6QYkccd3o?t=1938)
  > I'm actually looking a lot right now for people. What's their unlearning rate? Like how fast can they learn something and then walk away from it? Based on maybe what they're seeing when they test their product or something. So unlearning rate is one. Another one I'm interested in, I read a book a year
- Evidence: [Billion-Dollar Tech CEO: How To Make AI Work Like 100 Employ at 28:29](https://youtu.be/8ol3j7o1U7o?t=1709)
  > together, and being an analyst performing this task is slowly going to reduce. And you will though move towards a little bit more higher order of understanding of the questions that you want to ask. that is so true so this happened with me recently with ai agents getting more and more like with ai
- Evidence: [Ex-IMF Chief Economist: How USA Debt Triggers a Global Crisi at 1:29:03](https://youtu.be/dNIef2fGLQY?t=5343)
  > Now you have like a brilliant classmate on a phone or in your machine and that's what's happening is that students are saying, well, I don't need people to be surrounded by people, but I can just use Cloud or one of these other ones to do it. And I think that is a mistake

### sy06: How do the guests say you can tell a prospect is not a good fit?
- Split: dev  |  Author: claude
- **Gold answer:** Jen Abel says that on about one in four calls the gap between the prospect's maturity and hers is too big, so she suggests revisiting in a year. Rob Snyder says you can tell prospects they do not look like your case study, so it will be a lot of work and might not be a good fit.
- Key points: gap too big; revisit later; does not look like a case study
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 25:44](https://youtu.be/YS9In813jJ0?t=1544)
  > Yeah, there's something real. One out of every four calls, I'm like, listen, based off of the maturity of where you guys are and where we are, it's too much of a gap. Like, I'd love to revisit this in a year, like once you guys have a chance to like solve for X, Y,
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 1:15:21](https://youtu.be/19qrLchbQEc?t=4521)
  > And so it becomes this kind of tool. And you can say, you don't look like our case study. So it's probably going to be a lot of work and it might not be a good fit. And you can use it for qualification, disqualification, and for people to understand what you do. That's, that's

### sy07: What do the guests say about how and when to charge customers?
- Split: dev  |  Author: claude
- **Gold answer:** Jen Abel says price should follow the sales cycle, for example closing in 90 days at 100K, and that for a 30-day value case you charge and credit it back. In the $1M solo business episode the speaker describes charging a business owner $25,000 for an implementation, collecting half up front and half at the end.
- Key points: price follows sales cycle; charge and credit back; half up front
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 59:37](https://youtu.be/YS9In813jJ0?t=3577)
  > Your price should be predicated on your sales cycle, right? Like if you can get a deal done in 90 days for 100K, do that all the time, right? If it takes nine months to get a deal done, you probably should be charging 250, 300K. What are your thoughts on forward deployed engineers as
- Evidence: [The $1M+ Solo Grok Bot Business (Full Course) at 15:20](https://youtu.be/67BmkptgTms?t=920)
  > Maybe you collect half of that up front and then the other half at the end of the implementation of this. But let's go through the entire build out process, shall we? Let's do it. So first things first, I want to kind of walk through how I build in general because it's a principle

### sy08: How do the guests describe giving an AI agent the context it needs?
- Split: dev  |  Author: claude
- **Gold answer:** The AI Agents Full Course says an agent harness connects the model to your tools and all the context, with memory that builds over time. In the wrappers episode the guest says the key is getting the right context from the user, expressing the AI's output well, and making the model's job easy.
- Key points: harness connects context; memory builds up; get context from the user
- Evidence: [AI Agents Full Course 59 Minutes (for beginners) at 6:14](https://youtu.be/eA9Zf2-qYYM?t=374)
  > It connects in all your tools and then it connects in all the context. And a platform that facilitates this process and basically facilitates this loop to happen is known as an agent harness. And all of the popular AI agent platforms on the market that you'd be familiar with are just agent harnesses. They're
- Evidence: [Stop building AI wrappers. Start building agent harnesses. at 24:47](https://youtu.be/st61aKW8P5A?t=1487)
  > Can you get the right context from the user? Can you express the AI's output to the user in the right way? And can you distill all that into things that make the LLM's job really easy? When you make the LLM's job really easy, you can use any off-the-shelf model and get good results.

### sy09: What do the guests say about building software quickly with AI coding agents?
- Split: heldout  |  Author: claude
- **Gold answer:** The speaker in the $1M solo business episode walks through how he built a product in a weekend and what he could charge for it. In the Grok Bot episode the guest describes working out a pivot for his Pluto app with a friend who used Claude Code.
- Key points: built in a weekend; Pluto pivot with Claude Code
- Evidence: [The $1M+ Solo Grok Bot Business (Full Course) at 15:08](https://youtu.be/67BmkptgTms?t=908)
  > And now I want to kind of walk through how the hell did I build this in a weekend? How can you do it too? What is the kind of offer that I would take to a business owner to charge $25,000 up front? Maybe you collect half of that up front and then the
- Evidence: [I'm Obsessed With Grok Bot. Here's Why at 5:06](https://youtu.be/1cWZ7Ekff6E?t=306)
  > I'll give you a very clear example. Pluto is one of my apps that I've been working on for some time, and we're doing a slight pivot. And the pivot is basically we want to be able for people to use Pluto, and then with the data that is in the Pluto app and their

### sy10: How do the guests suggest deciding who to approach first when selling or distributing a product?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** Sachin Puri suggests asking an AI which markets use the product, who the customers are and which channels reach them, then building a profile of 10 to 20 partner companies. Jen Abel says to work out who carries weight in the buyer's company: the general counsel or head of legal at the top, with VPs and directors beneath.
- Key points: markets, customers, channels; 10 to 20 partners; head of legal, VPs, directors
- Evidence: [Billion-Dollar Tech CEO: How To Make AI Work Like 100 Employ at 1:06:36](https://youtu.be/8ol3j7o1U7o?t=3996)
  > what are the top markets in which this product has been used? Who are the customers who are using this? Okay. What are the different channels through which they are getting access to these services? Give me the names of, build me a full profile of 10, 20 people, companies in each of those markets
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 0:09](https://youtu.be/YS9In813jJ0?t=9)
  > Let's set this up. Let's start with how do I even get the first meeting? We're in this flood the zone moment of everyone trying to break into the enterprise. But like, what exactly are you solving for them as a problem that's level one, but most importantly, the alpha? And it needs to be

### sy11: How do the guests get AI agents to produce work that matches a particular look?
- Split: dev  |  Author: claude
- **Gold answer:** In the Grok Bot episode the guest has an agent build a design system, a guidebook of fonts, colours, spacing and shapes taken from a site he likes. In the $1M solo business episode the speaker keeps a swipe file of reference screenshots and sends screenshots to his agent.
- Key points: design system guidebook; swipe file; screenshots as references
- Evidence: [I'm Obsessed With Grok Bot. Here's Why at 24:25](https://youtu.be/1cWZ7Ekff6E?t=1465)
  > And for people who don't know what a design system is, it's basically a guidebook that a designer creates for developers. In this case, we're creating it for our agents, right? So we're telling the agent, this is the font it needs to use. These are the colors. This is the typography. These are the
- Evidence: [The $1M+ Solo Grok Bot Business (Full Course) at 25:13](https://youtu.be/67BmkptgTms?t=1513)
  > Okay, let's wrap. The screenshot bit is like, in general, if you're building anything, you want a swipe file. A swipe file is a place where you have references, screenshots on copy and design. And then you'll feed those to... to the LLMs or to paper to help get the most out of it. Yeah.

### sy12: How do different guests describe what an agent harness is or why it matters?
- Split: heldout  |  Author: claude
- **Gold answer:** The AI Agents Full Course defines it as the platform that runs the loop, with a model that keeps going until the task is done, connected to tools and context. In the wrappers episode the guest says the whole game is harness building: get the right context, express the output well, and distil it so an off-the-shelf model does well.
- Key points: platform running the loop; tools and context; harness building is the game
- Evidence: [AI Agents Full Course 59 Minutes (for beginners) at 6:21](https://youtu.be/eA9Zf2-qYYM?t=381)
  > facilitates this process and basically facilitates this loop to happen is known as an agent harness. And all of the popular AI agent platforms on the market that you'd be familiar with are just agent harnesses. They're just applications where this loop is facilitated. And I want to actually run this little prompt I prepared
- Evidence: [Stop building AI wrappers. Start building agent harnesses. at 24:42](https://youtu.be/st61aKW8P5A?t=1482)
  > I really view that as kind of the whole game here of just, and it comes back to harness building. Can you get the right context from the user? Can you express the AI's output to the user in the right way? And can you distill all that into things that make the LLM's job

### sy13: What role does a friendly contact or champion inside the buyer's company play in closing a deal?
- Split: dev  |  Author: claude
- **Gold answer:** Rob Snyder says that in larger deals a champion with pull decides they want it and then helps with the project management of getting it done. Jen Abel says that as soon as the demo ends you text the person who has guided you, to get a raw debrief on how it went and whether someone was lost.
- Key points: champion with pull; project management; debrief after a demo
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 57:10](https://youtu.be/19qrLchbQEc?t=3430)
  > And so in bigger deals, enterprise deals, there's like the champion has pull and decides, yes, I want this. And then you have to do a set of like 17 demos. You have to genuflect in front of four committees. Like there's all of these things that you have to do for smaller deals. You
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 46:58](https://youtu.be/YS9In813jJ0?t=2818)
  > So as soon as the demo closes, you are texting the woman or the gentleman or whomever that has helped guide you to this point. How do you think that went? Can we grab, can I call you in like five minutes? I just want to, I want like a fresh debrief. They will give


## Who / when said it (10)

### ww01: When does Rob Snyder describe getting the prospect's approval of the call agenda?
- Split: dev  |  Author: claude
- **Gold answer:** At about 43:08 in the episode.
- Key points: agenda approval
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 43:08](https://youtu.be/19qrLchbQEc?t=2588)
  > Does that sound good to you? Get their thumbs up on the agenda. And then you earn the right to ask them some discovery questions about their poll by saying, great. Okay. Before we get to those items on your You know, on our agenda. Do you mind if I ask you a few questions

### ww02: When does the host raise the idea that starting with services can be a good way to begin?
- Split: heldout  |  Author: claude
- **Gold answer:** At about 1:00:01. The host (Lenny) raises it, reacting to Rob's point.
- Key points: host raises services idea
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 1:00:01](https://youtu.be/19qrLchbQEc?t=3601)
  > this idea of services being a great place to start, which historically has been a terrible idea because the fear is you never actually get to a place where you can automate it and you're just running a consulting business forever with terrible margins. So you've seen this work, this idea of starting with basically

### ww03: When does the guest explain charging up front for the 30-day value case and crediting it back?
- Split: dev  |  Author: claude
- **Gold answer:** At about 59:24 in the episode.
- Key points: charge and credit back
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 59:24](https://youtu.be/YS9In813jJ0?t=3564)
  > For the 30-day value, charge and credit it back to them, but know that your sales cycle is going to probably be a month longer because that. But that's okay because you're probably charging more anyway. Got it. And just do the work to like integrate enough to make it magical. Your price should be

### ww04: Who brings up the idea of a dedicated frontier team, and at what point?
- Split: dev  |  Author: claude
- **Gold answer:** At about 43:44. The host (Lenny) brings it up, citing Dan Shipper's talk, and asks Josh how he feels about it.
- Key points: Dan Shipper; frontier team
- Evidence: [Why every company now needs to think and operate like a lab  at 43:44](https://youtu.be/3I6QYkccd3o?t=2624)
  > And Dan Shipper gave this really interesting talk about how to build where the tech is just constantly changing underneath you. And his advice is to have a frontier team that's dedicated to testing out the new stuff. And basically it's their job, trial the new stuff, report on what we need to pay attention

### ww05: When does Vinh Giang talk about a closed soft palate in connection with speaking louder?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** At about 43:08 in the episode.
- Key points: soft palate; volume
- Evidence: [Why Your Communication Makes People Ignore You & How To Fix  at 43:08](https://youtu.be/BgeNDG5jD60?t=2588)
  > your entire life, sometimes you've developed the habit of speaking with a closed soft palate. Okay. So, are your hands clean? Yeah. Okay, good. Take your thumb, touch the part behind your teeth. It's hard, right? That's your hard palate. Okay. Then slide it back a little bit more. Do you feel like a softer

### ww06: At what point does Vinh Giang tell the story about being silent with a relative who has cancer?
- Split: heldout `raj`  |  Author: claude
- **Gold answer:** At about 1:40:02 in the episode.
- Key points: family members; cancer; silence
- Evidence: [Why Your Communication Makes People Ignore You & How To Fix  at 1:40:02](https://youtu.be/BgeNDG5jD60?t=6002)
  > I've currently in my life have two family members who are going through cancer and if you're going through this with someone you love, it's one of the hardest things to go through because as the person on the outside, there's nothing you can do. You know, they have to fight the battle. She has

### ww07: When does the presenter explain that an agent's memory works differently from a chat model's?
- Split: dev  |  Author: claude
- **Gold answer:** At about 18:07 in the episode.
- Key points: agent memory vs chat memory
- Evidence: [AI Agents Full Course 59 Minutes (for beginners) at 18:07](https://youtu.be/eA9Zf2-qYYM?t=1087)
  > be a bit of a shock moving from chat to agents is that these agents memory work a little bit different so if you're used to using chat models like chat gpt and Claude if you open up a fresh session in the one of these chats you don't give it any context you don't

### ww08: When does the guest describe giving his editor casual feedback that a video looks too yellow?
- Split: dev  |  Author: claude
- **Gold answer:** At about 34:24 in the episode.
- Key points: editor feedback; too yellow
- Evidence: [I'm Obsessed With Grok Bot. Here's Why at 34:24](https://youtu.be/1cWZ7Ekff6E?t=2064)
  > I don't know what none of that means. So what I literally will do in my very, like, broken editor language English, I will tell it I want this, this feels a little too yellow, whatever. And guess what I do? I send it to my editor. And my editor, very, very talented, amazing, will

### ww09: When is the loop described in which a vision model approves or rejects a generated ad?
- Split: heldout  |  Author: claude
- **Gold answer:** At about 45:48 in the episode.
- Key points: vision model loop; two to three rounds
- Evidence: [AI Agents are too good at marketing now at 45:48](https://youtu.be/uJuxenfe-NU?t=2748)
  > And it goes in a like recursive loop, modifying the creative based off of that. So creative, you know, one gets made, one, Vision model looks. Yes, no. Okay, send it back. Make these changes. Yes, no. And it just goes, you know... We typically get it in like two to three. So it's like

### ww10: At what point does the guest explain why everything started to look like his company's output?
- Split: dev  |  Author: claude
- **Gold answer:** At about 14:58 in the episode.
- Key points: AI smells; Gamma look
- Evidence: [Stop building AI wrappers. Start building agent harnesses. at 14:58](https://youtu.be/st61aKW8P5A?t=898)
  > But once everybody started using it, everything started to look like gamma and people didn't want to be recognized as using AI. And so kind of our whole goal of this launch we just pulled off was we need to rapidly expand our sort of creative landscape. The truth is there's still going to be


## Unanswerable (on-topic, not in the library) (7)

### un01: How does Jen Abel say to design a pricing page for enterprise plans?
- Split: dev  |  Author: claude
- **Gold answer:** Not covered anywhere in the library or the held-out episodes. The right answer is that it is not found.
- Search phrases (must be absent): pricing page; enterprise plans

### un02: What does Rob Snyder say about meeting SOC 2 security requirements before selling to enterprises?
- Split: heldout  |  Author: claude
- **Gold answer:** Not covered. The right answer is that it is not found.
- Search phrases (must be absent): SOC 2

### un03: What did Gita Gopinath say about Bitcoin and stablecoins?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** Not covered. The right answer is that it is not found.
- Search phrases (must be absent): bitcoin; stablecoins

### un04: What does Sachin Puri say about taking his company public on the stock market?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** Not covered. The right answer is that it is not found.
- Search phrases (must be absent): go public

### un05: How does Josh Woodward's Labs team use Kubernetes to deploy its experiments?
- Split: dev  |  Author: claude
- **Gold answer:** Not covered. The right answer is that it is not found.
- Search phrases (must be absent): kubernetes

### un06: How does Vinh Giang recommend booking guests for a podcast?
- Split: heldout `raj`  |  Author: claude
- **Gold answer:** Not covered. The right answer is that it is not found.
- Search phrases (must be absent): booking guests

### un07: Which video editing software does the guest in the Grok Bot episode recommend?
- Split: dev  |  Author: claude
- **Gold answer:** Not covered. The right answer is that it is not found.
- Search phrases (must be absent): video editing software


## False premise (5)

### fp01: Why does Jen Abel say you should never offer a free trial?
- Split: dev  |  Author: claude
- **Gold answer:** She does not say this; she talks about charging and crediting back, and a free month as an incentive. The answer must correct the premise.
- Search phrases (must be absent): free trial

### fp02: Why did Josh Woodward say Google should shut down Labs?
- Split: heldout  |  Author: claude
- **Gold answer:** He does not say this. The answer must correct the premise.
- Search phrases (must be absent): shut down; labs

### fp03: Why does Rob Snyder say sales calls are a waste of time?
- Split: dev  |  Author: claude
- **Gold answer:** He does not say this; he teaches how to run calls. The answer must correct the premise.
- Search phrases (must be absent): sales calls; waste of time

### fp04: Why did Gita Gopinath say the IMF has defaulted on its loans?
- Split: heldout `raj`  |  Author: claude
- **Gold answer:** She says the opposite: nobody has ever defaulted to the IMF. The answer must correct the premise.
- Search phrases (must be absent): defaulted on; loans

### fp05: Why does Vinh Giang say you should avoid telling personal stories?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** He says to document your stories. The answer must correct the premise.
- Search phrases (must be absent): avoid telling


## Indexed but not in the evaluation library (5)

### nl01: What did the nutrition expert say about salt and blood pressure?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** Only in 'Diet Expert' (Raj Shamani), which is not in the evaluation library. The right answer is that it is not found in the library.
- Evidence: [Diet Expert: Weight Loss, Calories, Digestion, Sugar & Belly at 18:41](https://youtu.be/xi-zHJL5bnI?t=1121)
  > Sodium is not the culprit. it. It was demonized so that sugar could shine and diseases could flourish. Yes, sadly. Salt is never was never ill. If you have excess salt, it'll come out in your urine. If you have excess sugar, does it just come out in your urine? It gets stored as fat.

### nl02: What does the researcher say about thinking of AI models as an entity or as a tool?
- Split: heldout  |  Author: claude
- **Gold answer:** Only in 'Inside the black box of AI', which is not in the library. The right answer is that it is not found.
- Evidence: [Inside the black box of AI: How AI models actually think | E at 42:38](https://youtu.be/JHo-aiePjoM?t=2558)
  > or at least as we're thinking about more is this sort of question of anthropomorphization, you know, like, should you think of the models as like, should you model the model as like something that's closer to some like entity or closer to a tool? And I actually think that. Both are wrong. There's a

### nl03: Why did the Meta team keep the Jolly avatar instead of a corporate logo?
- Split: dev  |  Author: claude
- **Gold answer:** Only in 'Meta's Muse', which is not in the library. The right answer is that it is not found.
- Evidence: [Meta’s Muse: How we launched the most successful consumer pr at 26:59](https://youtu.be/WY0cdD4gNoQ?t=1619)
  > And so in the end, I think between Mark and us and a bunch of others, we were like, Jolly stays. I think this was like a week before launch or something. We were like, this is what we're going with. And I don't think we knew how iconic it was going to end up

### nl04: What was the story behind the Fitzpatrick scale and the Monk skin tone work?
- Split: heldout  |  Author: claude
- **Gold answer:** Only in 'Why PMs are suddenly valuable again', which is not in the library. The right answer is that it is not found.
- Evidence: [Why PMs are suddenly valuable again | Tulsee Doshi (Head of  at 26:41](https://youtu.be/qGf2Yvan4Wg?t=1601)
  > So one is you worked on something called the Fitzpatrick scale and the monk skin tone. And this was a big shift in how people in how models worked around and evals were a core part of this. Share this story. What this work was. Yeah. So I like like you noted earlier, I spent

### nl05: What should a business do this week to get ready for AI shopping agents?
- Split: dev  |  Author: claude
- **Gold answer:** Only in 'The 9 Stages of AI Agent Adoption', which is not in the library. The right answer is that it is not found.
- Evidence: [The 9 Stages of AI Agent Adoption, Explained at 22:15](https://youtu.be/nRl-7Yhmbog?t=1335)
  > I would just... First, run an agent test. Go into your support inbox, pull 10 real buying questions. Does this fit the older model? Can I get 12 of these by Friday? Give each one to two or three different agents and watch what happens. Where does it get stuck? That exercise is going to
