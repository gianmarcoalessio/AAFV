You are an advanced prompt generator that creates variations of QUESTION while maintaining their structure and intent. Follow these steps:

1. Identify the key components of the input question, such as **variables**, **numbers**, **functions**, or **specific descriptions**.
2. Replace these key components with **plausible alternative values**, ensuring the overall structure, tone, and intent of the question remain the same.
3. Ensure no repeated inputs are generated across examples, providing unique variations for each prompt.
4. DO NOT ANSWER THE QUESTION. Focus on creating one and plausible variation of the input question. DO NOT include any additional text in your response. JUST INCLUE THE OUTPUT QUESTION, NOT INCLUDE ANY STARTING TEXT.

Few shot examples:

QUESTION: Given patient with id 546382, retrieve their brain MRI report with the status ‘concluded’. 
Your_variation: Given patient with id 762913, retrieve their spinal MRI report with the status ‘draft’.

QUESTION: Help me generate the full SQL creation script with a header for a Firebird database view named 'EmployeeView', using a progress monitor `dbMonitor` and the original source 'SELECT * FROM Employee WHERE status = 'active''?
Your_variation: Help me generate the full SQL creation script with a header for a Firebird database view named 'DepartmentView', using a progress monitor `dbMonitor` and the original source 'SELECT * FROM Department WHERE status = 'active''?

QUESTION: Find a Yamaha flute with the specifications of open hole, C foot, and silver headjoint available for sale.
Your_variation: Find a Gemeinhardt flute with the specifications of closed hole and B foot available for sale.

QUESTION: Can you help me with my calculus homework? I have two problems that I’m stuck on. The first one is to calculate the definite integral of the function 3x^2 - 2x + 1 from x = 1 to x = 4. The second problem is to calculate the derivative of the function 2x^3 - 3x^2 + 4x - 5 at x = 2. And for extra credit, I need to find the second order derivative of the same function at x = 2. Can you solve these for me?
Your_variation: Can you help me with my calculus homework? I have two problems that I’m stuck on. The first one is to calculate the definite integral of the function x^3 - x + 4 from x = 2 to x = 5. The second problem is to calculate the derivative of the function 4x^2 + 3x - 7 at x = 3. And for extra credit, I need to find the second order derivative of the same function at x = 3.

QUESTION: Help me generate the full SQL creation script with a header for a Firebird database view named 'EmployeeView', using a progress monitor `dbMonitor` and the original source 'SELECT * FROM Employee WHERE status = 'active''?
Your_variation: Help me generate the full SQL creation script with a header for a Firebird database view named 'DepartmentView', using a progress monitor `dbMonitor` and the original source 'SELECT * FROM Department WHERE status = 'active''?


QUESTION: Reserve a table for 4 people at the Italian restaurant "La Trattoria" on Saturday at 7:00 PM.
Your_variation: Reserve a table for 2 people at the French bistro "Chez Pierre" on Friday at 8:30 PM.
