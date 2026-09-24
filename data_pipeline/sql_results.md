# SQL queries and outputs

### Q1 SELECT + WHERE: in-stock books priced above 40 GBP

```sql
SELECT title, price_gbp, rating
FROM books
WHERE in_stock = 1 AND price_gbp > 40
```

Rows returned: 30

```
                                                                   title  price_gbp  rating
                                                 It's Only the Himalayas      45.17       2
        Full Moon over Noah’s Ark: An Odyssey to Mount Ararat and Beyond      49.43       4
      See America: A Celebration of Our National Parks & Treasured Sites      48.87       3
                                                      A Summer In Europe      44.34       2
                                        A Year in Provence (Provence #1)      56.88       4
                                                           Sharp Objects      47.82       4
                                                     The Past Never Ends      56.50       4
                         The Murder of Roger Ackroyd (Hercule Poirot #4)      44.10       4
                                          The Last Mile (Amos Decker #2)      54.21       2
                                  A Time of Torment (Charlie Parker #14)      48.35       5
                   Murder at the 42nd Street Library (Raymond Ambler #1)      54.36       4
                                           Boar Island (Anna Pigeon #19)      59.48       3
The Bachelor Girl's Guide to Murder (Herringford and Watts Mysteries #1)      52.30       5
                                                              The Exiled      43.45       3
  The No. 1 Ladies' Detective Agency (No. 1 Ladies' Detective Agency #1)      57.70       4
                                     1st to Die (Women's Murder Club #1)      53.98       1
                                                      Tipping the Velvet      53.74       1
                                 A Flight of Arrows (The Pathfinders #2)      55.53       5
                         Glory over Everything: Beyond The Kitchen House      45.84       3
                                        The Last Painting of Sara de Vos      55.55       2
                       The Guernsey Literary and Potato Peel Pie Society      49.53       1
                                                   Girl in the Blue Coat      46.83       2
                                                     While You Were Mine      41.32       5
                                                  The Pilgrim's Progress      50.26       2
                                                                 Candide      58.63       3
                                                             Animal Farm      57.22       3
                                               The Story of Hong Gildong      43.19       4
                                                       The Little Prince      45.42       2
                                                         Of Mice and Men      47.11       2
               Alice in Wonderland (Alice's Adventures in Wonderland #1)      55.53       1
```

### Q2 ORDER BY + LIMIT: 10 most expensive books (INR)

```sql
SELECT title, price_gbp, price_inr
FROM books
ORDER BY price_inr DESC, title
LIMIT 10
```

Rows returned: 10

```
                                                                 title  price_gbp  price_inr
                                         Boar Island (Anna Pigeon #19)      59.48    6275.14
                                                               Candide      58.63    6185.46
The No. 1 Ladies' Detective Agency (No. 1 Ladies' Detective Agency #1)      57.70    6087.35
                                                           Animal Farm      57.22    6036.71
                                      A Year in Provence (Provence #1)      56.88    6000.84
                                                   The Past Never Ends      56.50    5960.75
                                      The Last Painting of Sara de Vos      55.55    5860.52
                               A Flight of Arrows (The Pathfinders #2)      55.53    5858.42
             Alice in Wonderland (Alice's Adventures in Wonderland #1)      55.53    5858.42
                 Murder at the 42nd Street Library (Raymond Ambler #1)      54.36    5734.98
```

### Q3 DISTINCT: distinct star ratings present

```sql
SELECT DISTINCT rating
FROM books
ORDER BY rating
```

Rows returned: 5

```
 rating
      1
      2
      3
      4
      5
```

### Q4 IN: books in Travel or Mystery

```sql
SELECT title, category_id, price_gbp
FROM books
WHERE category_id IN (SELECT category_id FROM categories
                      WHERE category_name IN ('Travel', 'Mystery'))
ORDER BY title
LIMIT 15
```

Rows returned: 15

```
                                                           title  category_id  price_gbp
                              1,000 Places to See Before You Die            4      26.08
                             1st to Die (Women's Murder Club #1)            3      53.98
                                                A Murder in Time            3      16.64
                         A Study in Scarlet (Sherlock Holmes #1)            3      16.73
                                              A Summer In Europe            4      44.34
                          A Time of Torment (Charlie Parker #14)            3      48.35
                                A Year in Provence (Provence #1)            4      56.88
                            Blood Defense (Samantha Brinkman #1)            3      20.30
                                   Boar Island (Anna Pigeon #19)            3      59.48
                             Career of Evil (Cormoran Strike #3)            3      24.72
                Delivering the Truth (Quaker Midwife Mystery #1)            3      20.89
                              Extreme Prey (Lucas Davenport #26)            3      25.40
Full Moon over Noah’s Ark: An Odyssey to Mount Ararat and Beyond            4      49.43
                                      Hide Away (Eve Duncan #20)            3      11.84
                                            In a Dark, Dark Wood            3      19.63
```

### Q5 BETWEEN: books priced 20-30 GBP with rating 4-5

```sql
SELECT title, price_gbp, rating
FROM books
WHERE price_gbp BETWEEN 20 AND 30 AND rating BETWEEN 4 AND 5
ORDER BY price_gbp, title
```

Rows returned: 12

```
                                                                        title  price_gbp  rating
                                                       Between Shades of Gray      20.79       5
                             Delivering the Truth (Quaker Midwife Mystery #1)      20.89       4
                                                       Voyager (Outlander #3)      21.07       5
                                            The Silkworm (Cormoran Strike #2)      23.05       5
                          The Mysterious Affair at Styles (Hercule Poirot #1)      24.80       4
            What Happened on Beale Street (Secrets of the South Mysteries #2)      25.37       5
                                           1,000 Places to See Before You Die      26.08       5
The Complete Stories and Poems (The Works of Edgar Allan Poe [Cameo Edition])      26.78       4
                                                        Lost Among the Living      27.70       4
                                               Little Women (Little Women #1)      28.07       4
                                                    The Marriage of Opposites      28.08       4
                                                        The Passion of Dolssa      28.32       5
```

### Q6 JOIN: 10 highest-rated books per category

```sql
SELECT category_name, title, rating, price_gbp
FROM (
    SELECT c.category_name, b.title, b.rating, b.price_gbp,
           ROW_NUMBER() OVER (
               PARTITION BY c.category_id
               ORDER BY b.rating DESC, b.price_gbp DESC, b.title
           ) AS rn
    FROM books b
    JOIN categories c ON c.category_id = b.category_id
)
WHERE rn <= 10
ORDER BY category_name, rn
```

Rows returned: 40

```
     category_name                                                                         title  rating  price_gbp
          Classics                                                     The Story of Hong Gildong       4      43.19
          Classics                                                Little Women (Little Women #1)       4      28.07
          Classics The Complete Stories and Poems (The Works of Edgar Allan Poe [Cameo Edition])       4      26.78
          Classics                                                             The Secret Garden       4      15.08
          Classics                                                                       Candide       3      58.63
          Classics                                                                   Animal Farm       3      57.22
          Classics                                                            Gone with the Wind       3      32.49
          Classics                                                             Wuthering Heights       3      17.73
          Classics                                                        The Pilgrim's Progress       2      50.26
          Classics                                                               Of Mice and Men       2      47.11
Historical Fiction                                       A Flight of Arrows (The Pathfinders #2)       5      55.53
Historical Fiction                                                           While You Were Mine       5      41.32
Historical Fiction                                                                  The Red Tent       5      35.66
Historical Fiction                                                                  Mrs. Houdini       5      30.25
Historical Fiction                                                         The Passion of Dolssa       5      28.32
Historical Fiction                                                        Voyager (Outlander #3)       5      21.07
Historical Fiction                                                        Between Shades of Gray       5      20.79
Historical Fiction                             A Spy's Devotion (The Regency Spies of London #1)       5      16.97
Historical Fiction                                                             A Paris Apartment       4      39.01
Historical Fiction                               World Without End (The Pillars of the Earth #2)       4      32.97
           Mystery      The Bachelor Girl's Guide to Murder (Herringford and Watts Mysteries #1)       5      52.30
           Mystery                                        A Time of Torment (Charlie Parker #14)       5      48.35
           Mystery             What Happened on Beale Street (Secrets of the South Mysteries #2)       5      25.37
           Mystery                                             The Silkworm (Cormoran Strike #2)       5      23.05
           Mystery                                                             The Girl You Lost       5      12.29
           Mystery        The No. 1 Ladies' Detective Agency (No. 1 Ladies' Detective Agency #1)       4      57.70
           Mystery                                                           The Past Never Ends       4      56.50
           Mystery                         Murder at the 42nd Street Library (Raymond Ambler #1)       4      54.36
           Mystery                                                                 Sharp Objects       4      47.82
           Mystery                               The Murder of Roger Ackroyd (Hercule Poirot #4)       4      44.10
            Travel                                            1,000 Places to See Before You Die       5      26.08
            Travel                                              A Year in Provence (Provence #1)       4      56.88
            Travel              Full Moon over Noah’s Ark: An Odyssey to Mount Ararat and Beyond       4      49.43
            Travel            See America: A Celebration of Our National Parks & Treasured Sites       3      48.87
            Travel                                     Neither Here nor There: Travels in Europe       3      38.95
            Travel                                                          Under the Tuscan Sun       3      37.33
            Travel                                                       It's Only the Himalayas       2      45.17
            Travel                                                            A Summer In Europe       2      44.34
            Travel           Vagabonding: An Uncommon Guide to the Art of Long-Term World Travel       2      36.94
            Travel                                                      The Great Railway Bazaar       1      30.54
```

### pd.read_sql vs pd.merge (Q6, first 12 rows side by side)

Equivalent: **True** (all 40 rows compared)

```
 sql_category_name                                                                     sql_title  sql_rating  sql_price_gbp pandas_category_name                                                                  pandas_title  pandas_rating  pandas_price_gbp
          Classics                                                     The Story of Hong Gildong           4          43.19             Classics                                                     The Story of Hong Gildong              4             43.19
          Classics                                                Little Women (Little Women #1)           4          28.07             Classics                                                Little Women (Little Women #1)              4             28.07
          Classics The Complete Stories and Poems (The Works of Edgar Allan Poe [Cameo Edition])           4          26.78             Classics The Complete Stories and Poems (The Works of Edgar Allan Poe [Cameo Edition])              4             26.78
          Classics                                                             The Secret Garden           4          15.08             Classics                                                             The Secret Garden              4             15.08
          Classics                                                                       Candide           3          58.63             Classics                                                                       Candide              3             58.63
          Classics                                                                   Animal Farm           3          57.22             Classics                                                                   Animal Farm              3             57.22
          Classics                                                            Gone with the Wind           3          32.49             Classics                                                            Gone with the Wind              3             32.49
          Classics                                                             Wuthering Heights           3          17.73             Classics                                                             Wuthering Heights              3             17.73
          Classics                                                        The Pilgrim's Progress           2          50.26             Classics                                                        The Pilgrim's Progress              2             50.26
          Classics                                                               Of Mice and Men           2          47.11             Classics                                                               Of Mice and Men              2             47.11
Historical Fiction                                       A Flight of Arrows (The Pathfinders #2)           5          55.53   Historical Fiction                                       A Flight of Arrows (The Pathfinders #2)              5             55.53
Historical Fiction                                                           While You Were Mine           5          41.32   Historical Fiction                                                           While You Were Mine              5             41.32
```
