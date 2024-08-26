
# Manufacturing Monitoring with Calendar Views

## Overview

This Odoo module provides a custom calendar view to monitor manufacturing operations. It tracks and displays various metrics related to products, including stock levels, orders, and manufacturing activities. The module updates in real-time based on stock pickings and manufacturing orders.

## Features

- **Custom Calendar Report**: Displays key metrics for each product on a daily basis.
- **Real-Time Updates**: Reflects changes in stock levels, orders, and manufacturing processes.
- **Metrics Tracked**:
  - Sale Order Quantity
  - Purchase Order Quantity
  - Stock on Hand
  - Being Manufactured
  - Reserved Quantity
  - BoM Quantity
  - Forecast Quantity

## Models

- **Custom Calendar Report**: Main model to store daily metrics for each product.
- **Stock Picking**: Inherits and extends stock picking functionality to update the custom calendar report.
- **Manufacturing Order**: Inherits and extends manufacturing order functionality to update the custom calendar report.


## Usage

- **Stock Pickings**: Updates the calendar report with sale and purchase quantities based on stock pickings.
- **Manufacturing Orders**: Updates the calendar report with manufacturing quantities and references.

## Logging

Logs are generated to track updates and changes. Check the Odoo log file for detailed information.

## License

This module is licensed under the MIT License.

