# General Purpose Management Intern - Internesh

Internesh is an autonomous agent that can be tasked to manage general tasks in your business, profession or personal life using a spreadsheet. It can learn workflows on the go and adapt its business logic if the problem space changes (like unexpected tasks, new requirements etc.). 

Internesh will present its current knowledge state in a spreadsheet so you can understand and track its actions.

### Use cases

Internesh as the name suggests is best suited for general tasks that are not domain specific and managerial in nature. Here are some examples:

- Managing your restaurant (taking orders, managing staff etc.)
- Managing an airbnb (checkin, bookings, maintenance etc.)
- Managing your warehouse for e-commerce (inventory, orders, shipments etc.)
- Managing your personal kitchen (stocking up, planning meals, tracking expenses etc.)
- Managing your art studio projects (tracking inventory, managing projects, tracking expenses etc.)

### It does not need to be programmed

Internesh works across domains out of the box. It does not need changes in its code to work when deployed for a certain task. It just needs to be fed instructions on what the job is, what tasks it can perform and how to perform them.

### Abilities 

Current knowledge is stored in a structured database, an elastic search engine and an adaptive in memory store (using [meTTa](https://singularitynet.io/metta-in-a-nutshell-exploring-the-language-of-agi/))

Using a combination of structured, unstructured and fuzzy matching, Internesh can:

1. Develop a structured schema based on the problem space (for example, a restaurant mananger role will require it to store menu items, orders, staff profiles etc.)
2. Learn and develop workflows i.e. actions it can perform along with instructions, business logic (eg. taking orders - only if item is available, processing salaries - only if attendance is confirmed etc.)
3. Process incoming requests by identifying workflow and using elastic search to identify relevant changes that need to be made in the structured database (eg. taking customer orders from messages like "Spicy burgers", "best vegetarian pizza options" etc.)
