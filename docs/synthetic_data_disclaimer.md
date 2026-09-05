# Synthetic data disclaimer

ChargebackOS does not contain real merchant, customer, card, or bank records.

The intended demonstration uses generator-produced merchants, customers, transactions, orders, evidence and outcomes (`seed = 42`). Additional dispute ingests must reference those stored synthetic records and receive no invented outcome labels. Hosted contents must be verified by the operator. Labels such as “friendly fraud likely” and simulated win/loss are **operational training labels**, not legal findings or issuer decisions.

This is required: real chargeback files are sensitive. The generator exists so the model, policy engine, and evaluation protocol can be inspected without exposing personal or payment data.

Do not treat simulated recovery rupees as a promise of production performance.

Staff accounts are separate from synthetic customers. Their passwords, session tokens and hosting credentials remain sensitive.
