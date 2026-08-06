# SupplyNet AI — Optimization Model

## Planning scope

Version 1 solves a single-week network planning problem.

The network contains:

- 25 suppliers
- 4 distribution centers
- 8 customer regions
- supplier-to-DC inbound transportation
- DC-to-region outbound transportation

Inbound transportation is booked by container.
Outbound transportation is priced per pallet.

---

# Sets

S = suppliers

D = distribution centers

R = customer regions

---

# Decision Variables

## Inbound pallets

x[s,d]

Number of pallets shipped from supplier s to DC d.

x[s,d] >= 0


## Containers booked

y[s,d]

Number of containers booked from supplier s to DC d.

y[s,d] >= 0 and integer


## Outbound pallets

z[d,r]

Number of pallets shipped from DC d to region r.

z[d,r] >= 0


## Ending inventory

I[d]

Pallets remaining at DC d after fulfillment.

I[d] >= 0


## Unmet demand

u[r]

Customer demand that could not be fulfilled.

u[r] >= 0

---

# Objective

Minimize total network cost:

Total Cost =
Inbound Transportation Cost
+ Outbound Transportation Cost
+ DC Handling Cost
+ Inventory Holding Cost
+ Shortage Cost

## Inbound transportation

sum(s,d) container_cost[s,d] * y[s,d]

## Outbound transportation

sum(d,r) outbound_cost[d,r] * z[d,r]

## Handling

sum(s,d) handling_cost[d] * x[s,d]

## Holding

sum(d) holding_cost[d] * I[d]

## Shortage

sum(r) shortage_penalty[r] * u[r]

---

# Constraints

## Supplier capacity

For every supplier:

sum(d) x[s,d] <= supplier_capacity[s]

---

## Container capacity

For every inbound lane:

x[s,d] <= pallets_per_container[s,d] * y[s,d]

---

## DC receiving capacity

For every DC:

sum(s) x[s,d] <= receiving_capacity[d]

---

## DC flow balance

For every DC:

initial_inventory[d]
+ sum(s) x[s,d]
=
sum(r) z[d,r]
+ I[d]

---

## DC storage capacity

For every DC:

I[d] <= storage_capacity[d]

---

## Customer demand

For every region:

sum(d) z[d,r] + u[r] = demand[r]

---

## Inbound lane availability

If supplier-to-DC lane is unavailable:

x[s,d] = 0
y[s,d] = 0

---

## Outbound lane availability

If DC-to-region lane is unavailable:

z[d,r] = 0

---

# Solver

Use OR-Tools CBC because the model includes integer container-booking variables.

This is a Mixed Integer Linear Programming problem.
