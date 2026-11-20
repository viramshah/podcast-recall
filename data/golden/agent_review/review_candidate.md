# Golden set candidate (rebalanced): review sheet (generated)

Regenerate with the script that wrote it, or read any item with `uv run podcast-recall eval show <id>`.

## How to review (about 3 hours)

For each question, decide: **keep**, **edit** or **replace**. Check four things:

1. **Would you really ask this?** Natural wording, not copied from the transcript. If not, rewrite it in your words.

2. **Is the gold answer right and complete?** Read the transcript text under it (and open the link if unsure). Fix the gold answer, or the time, in `data/golden/agent_review/golden_v0_candidate.csv`.

3. **Is the time inside the answer?** The link opens at the gold time. For a who/when question, the answer must be at that time.

4. **For the unanswerable, false-premise and not-in-library types:** is the answer truly absent from the library (or present only in a held-out episode)? `eval check` searches for the phrases listed.

**Your own questions:** at least a third of the final set (20 of 60) should be ones you write from memory. Replace a drafted question of the same type with yours, set `author` to `pm`, and keep the type counts (20 / 13 / 10 / 7 / 5 / 5). Questions you author from episodes in the library need `gold_evidence` as `video_id@mm:ss`.

Split: **dev** items may be used for tuning later; **heldout** items are only for the final gate. Don't use heldout items to tune anything.


## Single-fact lookup (20)

### n01: How does the US debt burden compare with Japan's, according to Gita Gopinath?
- Split: heldout `raj`  |  Author: agent_reviewer
- **Gold answer:** She says the US is not the most indebted large economy: Japan's debt is about 230% of GDP against about 100% for US federal debt. She adds that the absolute size of the debt is less interesting than its size relative to the economy.
- Key points: Japan about 230% of GDP; US federal about 100%; size relative to economy matters
- Evidence: [Ex-IMF Chief Economist: How USA Debt Triggers a Global Crisi at 18:19](https://youtu.be/dNIef2fGLQY?t=1099)
  > So, first of all, it's not the country with the most amount of debt. the country among the large economies that have very high levels of debt, Japan is the highest. So Japan's debt to GDP is around 230%. The US federal debt to GDP is around 100%. But the absolute number of the US

### n04: What is the TPU Harvester award that Josh Woodward gives to his team, and who gets it?
- Split: dev  |  Author: agent_reviewer
- **Gold answer:** It goes to people who do the grungy work of efficiency and reclaiming TPUs so the team can build the next features and fuel growth. Winners get a miniature rake and a cash award.
- Key points: reward efficiency work; reclaiming TPUs; miniature rake; cash award
- Evidence: [Why every company now needs to think and operate like a lab  at 58:32](https://youtu.be/3I6QYkccd3o?t=3512)
  > Share these awards you give and what they mean. Oh, yeah, yeah. So the TPU Harvester, we just need more and more TPUs as our products are growing. And a few of us wanted to figure out a way to reward people who do the grungy work. Of efficiency and reclaiming TPUs, harvesting TPUs so

### r01: Besides marketing, what else does Rob Snyder say a customer case study is useful for?
- Split: heldout  |  Author: claude
- **Gold answer:** He says a case study can be used to qualify and disqualify prospects, and to help people understand what you do: you can tell a prospect they do not look like your case study, so it would be a lot of work and might not be a good fit.
- Key points: qualification; disqualification; helps people understand what you do
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 1:15:27](https://youtu.be/19qrLchbQEc?t=4527)
  > And you can use it for qualification, disqualification, and for people to understand what you do. That's, that's funny. There's this whole theme now of building software factories, um, where, you know, product build itself, but, um, there's a really another version of a factory you're building, which is even the broader version of just

### r02: In the Grok Bot episode, roughly how much API credit does the guest say his $200 plan provides?
- Split: heldout  |  Author: claude
- **Gold answer:** About $8,000 worth of API credits for the $200 plan.
- Key points: about $8,000 of API credits; $200 plan
- Evidence: [I'm Obsessed With Grok Bot. Here's Why at 14:35](https://youtu.be/1cWZ7Ekff6E?t=875)
  > You're getting like $8,000 worth of API credits, right? So if $200 doesn't hurt the bank, It is absolutely responsible to not take advantage of the subsidy while it lasts. Now, someone might be asking, how am I using? How have I connected GrokBot to CloudCode? There's two easy ways to do it. There's two

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

### sf06: In what situations does Vinh Giang say you should write down a story you might tell later?
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

### sf15: In the beginner's AI agents course, how is a skill different from keeping something in an agent's memory?
- Split: dev  |  Author: claude
- **Gold answer:** A skill packages a whole process as a markdown file (for example writing a proposal) so it is done the same way each time; memory holds preferences and facts. Process material clogs memory and belongs in skills.
- Key points: skill = packaged process; memory = preferences
- Evidence: [AI Agents Full Course 59 Minutes (for beginners) at 41:25](https://youtu.be/eA9Zf2-qYYM?t=2485)
  > basically it packages up that process into a dot skill file and in that dot skill file it's basically just a marked down file that explains the exact process that you went through so you could create a proposal skill and then every time you now you need a proposal written it just takes that

### sf17: How does the guest connect his bot to Claude Code?
- Split: dev  |  Author: claude
- **Gold answer:** Easy way: tell the bot to log into Claude Code on its own computer. His way: a network of machines connected through Tailscale, using T3 Code.
- Key points: bot logs in itself; Tailscale network; T3 Code
- Evidence: [I'm Obsessed With Grok Bot. Here's Why at 14:51](https://youtu.be/1cWZ7Ekff6E?t=891)
  > How have I connected GrokBot to CloudCode? There's two easy ways to do it. There's two ways to do it. The easy way and the way I've done it. The easy way is every bot has a computer, right? So you can literally tell it, hey, log into CloudCode on your computer and it can

### sf18: In the Grok Bot episode, what did the bot do when the guest bought a PS5 Pro on eBay?
- Split: dev  |  Author: claude
- **Gold answer:** It emailed the eBay seller, negotiated for him and checked that the console was viable.
- Key points: emailed seller; negotiated; checked viability
- Evidence: [I'm Obsessed With Grok Bot. Here's Why at 43:26](https://youtu.be/1cWZ7Ekff6E?t=2606)
  > Greg? It was my GrokBot. GrokBot emailed the person who listed it on eBay, found out that it was a store in Ontario two hours away, gave me the number, gave me the script to talk to the person. Obviously, I didn't use the script. Called the person, confirmed. I gave it access. It bought


## Cross-episode synthesis (13)

### n06: What do the guests suggest for learning directly from customers what they want or why they bought?
- Split: dev `raj`  |  Author: agent_reviewer
- **Gold answer:** Sachin Puri suggests surveying buyers and, if you only have a handful, calling them to ask how they found you and why they chose you. Rob Snyder describes a company whose working product ideas all came from customers asking for something extra in sales calls, and advises talking to about five existing customers to look for pull.
- Key points: survey buyers; call customers; how did you find us; ideas from sales calls; talk to five customers
- Evidence: [Billion-Dollar Tech CEO: How To Make AI Work Like 100 Employ at 1:01:59](https://youtu.be/8ol3j7o1U7o?t=3719)
  > thing first who is this customer why did they buy their product where do i find that out how do i like somebody just bought something from my website how do i find that survey put a survey put a survey and if you have only handful of the customers just give them a call
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 1:18:10](https://youtu.be/19qrLchbQEc?t=4690)
  > I can't share the name, but a company was, a new product leader at a company was telling me, hey, yeah, the way we get our ideas, all of the ideas that have worked have come from sales calls where they said, cool, yeah, you can do X, but could you also do this other

### n07: What do the guests say to do when early evidence shows an idea is not working?
- Split: dev  |  Author: agent_reviewer
- **Gold answer:** Josh Woodward describes a Gemini feature whose early data was weak, where a PM said it should not launch; he praised her and says that when the team says it is not going, the answer is to pivot. Rob Snyder says that if five calls show no pull you ask a 'Hail Mary' question about anything on their to-do list, then do another set of five calls with a new pull hypothesis or go back for hands-on knowledge.
- Key points: early data weak; PM said do not launch; pivot; no pull after five calls; Hail Mary question; new pull hypothesis
- Evidence: [Why every company now needs to think and operate like a lab  at 18:51](https://youtu.be/3I6QYkccd3o?t=1131)
  > and be able to say like, hey, I don't think this is working. And yesterday, just as an example, we had a feature we were really excited about in Gemini we were gonna launch and we got some of the early data back. People went out, looked in the eyes and it just wasn't there.
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 1:05:54](https://youtu.be/19qrLchbQEc?t=3954)
  > go hands, hands on with some other small business sort of thing? Or what do you recommend? Yeah. So different pathways there. Hopefully you've asked the hail Mary question and you've learned something. That's like worth double clicking into. And the Hail Mary question is just like, what is there anything that we can do

### n09: What do the guests say about doing work for free to win a customer?
- Split: dev  |  Author: agent_reviewer
- **Gold answer:** Rob Snyder advises against free design partnerships because they lead to products that do not sell. The speaker in the $1M solo business episode suggests a free case study for, say, a dental clinic in exchange for introductions to three colleagues, and Jen Abel prefers to forgo money for a short two-to-three-day pilot to control the sales cycle, while charging for longer ones.
- Key points: no free design partnerships; free case study for introductions; two-to-three-day pilot; charge for longer pilots
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 58:35](https://youtu.be/19qrLchbQEc?t=3515)
  > I imagine your advice here, just like sell it directly. Don't try to give them for free. Don't set up some kind of partnership thing. Yeah. Why shoot yourself in the foot? And again, the reason not to is because you find it doesn't lead to the best, to stuff that actually sells and works,
- Evidence: [The $1M+ Solo Grok Bot Business (Full Course) at 44:38](https://youtu.be/67BmkptgTms?t=2678)
  > Yeah. Couldn't agree more. The one thing I'd add is if you are going to go and do a free case study for someone, say a dental clinic, one thing you can do is you can say, hey, I normally charge $50,000 a year for this service. I'm going to do this for you for
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 49:25](https://youtu.be/YS9In813jJ0?t=2965)
  > They're not the user. Who are the users of this? I want them to experience the magic and the power of what this is. You could charge them for a pilot if it's an extended period of time, but I'd rather forego the money and do a two to three day pilot so that at

### r03: How do the guests suggest finding out whether people really want a product before you build it?
- Split: heldout  |  Author: claude
- **Gold answer:** Rob Snyder says the signal to look for is a prospect leaning in, such as an executive who says they would pay right now before there is any product. The speaker in the $1M solo business episode says to test several industries and niches with people you know and see where the market appetite is.
- Key points: leaning-in signal; pay before the product exists; test niches and see the appetite
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 25:43](https://youtu.be/19qrLchbQEc?t=1543)
  > an exec in pharma, before he had a product said, if you can do that, I will pay you right now. So, okay, that's the signal you are looking for. What you're looking for as well as they're leaning in. Wait a second, you can do what? What you're not looking for is kind of
- Evidence: [The $1M+ Solo Grok Bot Business (Full Course) at 43:55](https://youtu.be/67BmkptgTms?t=2635)
  > Just try test out a bunch of them. See what the market appetite is with people that you know and build for them. And then once you're building for them, like just genuinely sit down. Don't try and scale right away. Sit down with that one first client. Try really to solve their business, watch

### r04: How do the guests describe using AI agents to stand in for staff roles?
- Split: heldout  |  Author: claude
- **Gold answer:** In the AI Agents Full Course the presenter sets up agents such as an executive assistant and a head of marketing, each with its own memory of preferences. In 'AI Agents are too good at marketing now' the speaker says you can solve the labour problem yourself, with no graphic designer, video editor or sales development rep.
- Key points: executive assistant; head of marketing; no designer, editor or SDR
- Evidence: [AI Agents Full Course 59 Minutes (for beginners) at 29:58](https://youtu.be/eA9Zf2-qYYM?t=1798)
  > clients on Slack I always want to keep client comms on email but if you're building out like a head of marketing it might be preferences about how you like your ads structured in Facebook manager if you're building if you've got a folder where you're working on a website or an app it might
- Evidence: [AI Agents are too good at marketing now at 3:09](https://youtu.be/uJuxenfe-NU?t=189)
  > So how do you co-work with this? But solve the labor problem for yourself, so you don't have to have a graphic designer, you don't have to have a video editor, you don't have to have a sales development rep. You go down the list, all these pieces can basically be handled and solved. So

### r05: How do the guests describe an AI agent asking the user for missing information before it starts work?
- Split: heldout  |  Author: claude
- **Gold answer:** In the wrappers episode the guest says their product pops up a form and asks a few questions, such as who the work is for, before it runs. In the AI Agents Full Course the agent, with an empty folder, asks what you sell, who you target and what tone you want.
- Key points: asks who it is for; form with questions; asks what you sell, target and tone
- Evidence: [Stop building AI wrappers. Start building agent harnesses. at 5:23](https://youtu.be/st61aKW8P5A?t=323)
  > And so typically we will actually pop up a form and ask a few questions. Questions like, who's this actually for? You know, is this like an educational presentation for school? Is this for adults? Is this for your work thing? We will actually call out often to different connectors. So we've built integrations into
- Evidence: [AI Agents Full Course 59 Minutes (for beginners) at 17:45](https://youtu.be/eA9Zf2-qYYM?t=1065)
  > nothing in the folder and it has no memory of our previous sessions um and it's asking like what like what do you even sell um and then we've got to kind of give it like who do you target what tone do you want this is all things that our executive assistant should know

### sy01: What do the guests say about working closely with early customers, even by hand, before trying to scale?
- Split: dev  |  Author: claude
- **Gold answer:** Rob Snyder says starting as a service, with humans doing the work by hand and automation built up around it, can work, though you can get stuck as a services business. The speaker in 'The $1M+ Solo Grok Bot Business' says not to scale right away: sit down with one first client, study their business and watch them.
- Key points: start by hand; one first client; do not scale too early
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 59:16](https://youtu.be/19qrLchbQEc?t=3556)
  > Yeah. And you can sell something that's like, you know, you might not have a full platform ready. You can sell something that's more service shaped early on. I've seen a bunch of startups do that where they sell, you know, okay, we're going to have an AI product manager who can do X, Y,
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

### sy07: How do the guests describe charging a customer money up front?
- Split: dev  |  Author: claude
- **Gold answer:** Jen Abel says that for a 30-day value case you charge up front and credit it back against the later contract, and that price should follow the sales cycle. In the $1M solo business episode the speaker describes charging a business owner $25,000 for an implementation, collecting half up front and the rest at the end.
- Key points: charge and credit back; price follows sales cycle; half up front, half at the end
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 59:37](https://youtu.be/YS9In813jJ0?t=3577)
  > Your price should be predicated on your sales cycle, right? Like if you can get a deal done in 90 days for 100K, do that all the time, right? If it takes nine months to get a deal done, you probably should be charging 250, 300K. What are your thoughts on forward deployed engineers as
- Evidence: [The $1M+ Solo Grok Bot Business (Full Course) at 15:20](https://youtu.be/67BmkptgTms?t=920)
  > Maybe you collect half of that up front and then the other half at the end of the implementation of this. But let's go through the entire build out process, shall we? Let's do it. So first things first, I want to kind of walk through how I build in general because it's a principle

### sy11: How do the guests get AI agents to produce work that matches a particular look?
- Split: dev  |  Author: claude
- **Gold answer:** In the Grok Bot episode the guest has an agent build a design system, a guidebook of fonts, colours, spacing and shapes taken from a site he likes. In the $1M solo business episode the speaker keeps a swipe file of reference screenshots and sends screenshots to his agent.
- Key points: design system guidebook; swipe file; screenshots as references
- Evidence: [I'm Obsessed With Grok Bot. Here's Why at 24:25](https://youtu.be/1cWZ7Ekff6E?t=1465)
  > And for people who don't know what a design system is, it's basically a guidebook that a designer creates for developers. In this case, we're creating it for our agents, right? So we're telling the agent, this is the font it needs to use. These are the colors. This is the typography. These are the
- Evidence: [The $1M+ Solo Grok Bot Business (Full Course) at 25:13](https://youtu.be/67BmkptgTms?t=1513)
  > Okay, let's wrap. The screenshot bit is like, in general, if you're building anything, you want a swipe file. A swipe file is a place where you have references, screenshots on copy and design. And then you'll feed those to... to the LLMs or to paper to help get the most out of it. Yeah.

### sy13: What role does a friendly contact or champion inside the buyer's company play in closing a deal?
- Split: dev  |  Author: claude
- **Gold answer:** Rob Snyder says that in larger deals a champion with pull decides they want it and then helps with the project management of getting it done. Jen Abel says that as soon as the demo ends you text the person who has guided you, to get a raw debrief on how it went and whether someone was lost.
- Key points: champion with pull; project management; debrief after a demo
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 57:10](https://youtu.be/19qrLchbQEc?t=3430)
  > And so in bigger deals, enterprise deals, there's like the champion has pull and decides, yes, I want this. And then you have to do a set of like 17 demos. You have to genuflect in front of four committees. Like there's all of these things that you have to do for smaller deals. You
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 46:58](https://youtu.be/YS9In813jJ0?t=2818)
  > So as soon as the demo closes, you are texting the woman or the gentleman or whomever that has helped guide you to this point. How do you think that went? Can we grab, can I call you in like five minutes? I just want to, I want like a fresh debrief. They will give


## Who / when said it (10)

### n13: When does Josh Woodward bring up Roger Federer, and what idea does he take from him?
- Split: dev  |  Author: agent_reviewer
- **Gold answer:** At about 32:24 he mentions a book about Federer and the phrase 'explosive endurance': people who can go really hard but pace themselves so they can keep going over time. He links this to his idea of an unlearning rate.
- Key points: Roger Federer book; explosive endurance
- Evidence: [Why every company now needs to think and operate like a lab  at 32:24](https://youtu.be/3I6QYkccd3o?t=1944)
  > Based on maybe what they're seeing when they test their product or something. So unlearning rate is one. Another one I'm interested in, I read a book a year or so ago about Roger Federer, the amazing tennis player. And there was this phrase in there about Federer had explosive endurance. It's just this beautiful

### r06: When does Jen Abel mention a small incentive, such as a free month, for signing by a set date?
- Split: heldout  |  Author: claude
- **Gold answer:** At about 1:14:38, in step 11 (papering prep), Jen Abel says to set a timeline for procurement and offer a small gift, such as a free month, if they sign by the date.
- Key points: step 11; procurement timeline; free month if signed by the date
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 1:14:39](https://youtu.be/YS9In813jJ0?t=4479)
  > Here's a little gift you'll get if you do it by the state, free month or whatever. Okay. Step 12, papering review. Yes. The best thing you can do is they're going to send you back red lines. No question. If the red lines are extensive, okay, go ahead and accept the things that are

### r07: When does the presenter point out that agent platforms are starting to offer scheduled tasks?
- Split: dev  |  Author: claude
- **Gold answer:** At about 45:34 the presenter of the AI Agents Full Course says that many agent harnesses are now starting to introduce scheduled tasks.
- Key points: scheduled tasks; agent harnesses
- Evidence: [AI Agents Full Course 59 Minutes (for beginners) at 45:35](https://youtu.be/eA9Zf2-qYYM?t=2735)
  > task because a lot of these agent harnesses now are starting to introduce scheduled tasks so you can just run it on 9am every morning use my daily brief skill to prepare me for my day but I think another cool one here just to show you an example right of how my new like

### ww01: When does Rob Snyder describe getting the prospect's approval of the call agenda?
- Split: dev  |  Author: claude
- **Gold answer:** At about 43:08 in the episode.
- Key points: agenda approval
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 43:08](https://youtu.be/19qrLchbQEc?t=2588)
  > Does that sound good to you? Get their thumbs up on the agenda. And then you earn the right to ask them some discovery questions about their poll by saying, great. Okay. Before we get to those items on your You know, on our agenda. Do you mind if I ask you a few questions

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

### n14: What does Gita Gopinath say about central banks buying gold?
- Split: dev `raj`  |  Author: agent_reviewer
- **Gold answer:** Not covered anywhere in the 16 episodes. The right answer is that it is not found.
- Search phrases (must be absent): gold; central banks buying gold; bullion; gold reserves

### n15: What does Rob Snyder say about whether a startup should raise venture capital before looking for pull?
- Split: dev  |  Author: agent_reviewer
- **Gold answer:** Not covered. The right answer is that it is not found.
- Search phrases (must be absent): raise venture capital; fundraising; seed round; investors

### n16: Does the AI Agents Full Course show how to build a customer support agent?
- Split: dev  |  Author: agent_reviewer
- **Gold answer:** Not covered. The right answer is that it is not found.
- Search phrases (must be absent): customer support agent; support tickets; help desk; customer service

### un01: How does Jen Abel say to design a pricing page for enterprise plans?
- Split: dev  |  Author: claude
- **Gold answer:** Not covered anywhere in the library or the held-out episodes. The right answer is that it is not found.
- Search phrases (must be absent): pricing page; enterprise plans

### un02: What does Rob Snyder say about meeting SOC 2 security requirements before selling to enterprises?
- Split: heldout  |  Author: claude
- **Gold answer:** Not covered. The right answer is that it is not found.
- Search phrases (must be absent): SOC 2

### un04: What does Sachin Puri say about taking his company public on the stock market?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** Not covered. The right answer is that it is not found.
- Search phrases (must be absent): go public

### un06: How does Vinh Giang recommend booking guests for a podcast?
- Split: heldout `raj`  |  Author: claude
- **Gold answer:** Not covered. The right answer is that it is not found.
- Search phrases (must be absent): booking guests


## False premise (5)

### fp04: Why does Gita Gopinath say countries regularly default on their IMF loans?
- Split: heldout `raj`  |  Author: claude
- **Gold answer:** She says the opposite: nobody has ever defaulted to the IMF. The answer must correct the premise.
- Search phrases (must be absent): defaulted on; loans

### fp05: Why does Vinh Giang say you should avoid telling personal stories?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** He says to document your stories. The answer must correct the premise.
- Search phrases (must be absent): avoid telling

### n18: Why does Rob Snyder say you should build the whole product before you start selling?
- Split: heldout  |  Author: agent_reviewer
- **Gold answer:** He does not say this; he says to test pull first by selling, even something service-shaped, before building. The answer must correct the premise.
- Search phrases (must be absent): build the whole product first; before selling; finish the product

### n19: Why does Vinh Giang say your accent is the main thing holding back your communication?
- Split: dev `raj`  |  Author: agent_reviewer
- **Gold answer:** He does not say this; he says he does not believe accents are a problem, and that an accent comes from carrying mouth movements over from another language, so learning new mouth movements makes you clearer. The answer must correct the premise.
- Search phrases (must be absent): accent is the problem; fix your accent; accent holds you back

### r08: Why does Josh Woodward say scheduled design sprints are the best source of new product ideas?
- Split: dev  |  Author: claude
- **Gold answer:** He says the opposite: good ideas very rarely come from design sprints or calendar slots set aside for ideas; they usually come when people are hacking and building on their own, in the hallway, at weekends or over a break. The answer must correct the premise.
- Search phrases (must be absent): design sprints are the best; best source of new ideas


## Indexed but not in the evaluation library (5)

### nl01: What did the nutrition expert say about salt and blood pressure?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** Only in 'Diet Expert' (Raj Shamani), which is not in the evaluation library. The right answer is that it is not found in the library.
- Evidence: [Diet Expert: Weight Loss, Calories, Digestion, Sugar & Belly at 17:42](https://youtu.be/xi-zHJL5bnI?t=1062)
  > sugar. Okay, think about it. Someone gets a stroke. Someone gets a heart attack. Or someone is just collapsed out of we don't know what. Rushed him in an ambulance. Without talking to any doctors, without knowing medical history, what do you add? Saline. Saline. What is that? Saline. What is saline? Glucose. Saline. What

### nl02: What does the researcher say about thinking of AI models as an entity or as a tool?
- Split: heldout  |  Author: claude
- **Gold answer:** Only in 'Inside the black box of AI', which is not in the library. The right answer is that it is not found.
- Evidence: [Inside the black box of AI: How AI models actually think | E at 42:38](https://youtu.be/JHo-aiePjoM?t=2558)
  > or at least as we're thinking about more is this sort of question of anthropomorphization, you know, like, should you think of the models as like, should you model the model as like something that's closer to some like entity or closer to a tool? And I actually think that. Both are wrong. There's a

### nl03: Why did the Meta team keep the Jolly avatar instead of a corporate logo?
- Split: dev  |  Author: claude
- **Gold answer:** Only in 'Meta's Muse', which is not in the library. The right answer is that it is not found.
- Evidence: [Meta’s Muse: How we launched the most successful consumer pr at 26:19](https://youtu.be/WY0cdD4gNoQ?t=1579)
  > And I would say that the reason there were so many reasons, but actually Mark was one of the reasons where he was like, no, he really loved the avatar. But I think mostly it's like when you're talking to something that feels so personal, the last thing you want to talk to is a

### nl04: What was the story behind the Fitzpatrick scale and the Monk skin tone work?
- Split: heldout  |  Author: claude
- **Gold answer:** Only in 'Why PMs are suddenly valuable again', which is not in the library. The right answer is that it is not found.
- Evidence: [Why PMs are suddenly valuable again | Tulsee Doshi (Head of  at 26:41](https://youtu.be/qGf2Yvan4Wg?t=1601)
  > So one is you worked on something called the Fitzpatrick scale and the monk skin tone. And this was a big shift in how people in how models worked around and evals were a core part of this. Share this story. What this work was. Yeah. So I like like you noted earlier, I spent

### r09: What are the nine stages of AI agent adoption?
- Split: dev  |  Author: claude
- **Gold answer:** Only in 'The 9 Stages of AI Agent Adoption', which is not in the evaluation library. The right answer is that it is not found in the library.
- Evidence: [The 9 Stages of AI Agent Adoption, Explained at 17:52](https://youtu.be/nRl-7Yhmbog?t=1072)
  > So here's how I think. The war on agents plays out, and I think there's going to be nine stages. I tweeted this. I got some people agreeing with me, some people who disagree with me. So let me know where you sit. Stage one is where companies... Block agents because agents are skipping ads
