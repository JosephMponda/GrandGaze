# System Design Document

![MUST logo](static/img/must-logo.png) ![GSL logo](static/img/logos/GSL-Official-Logo.png)

Grand Gaze

## Overview

This prototype is a modular EMR for a low-resource teaching hospital environment.
It supports phased growth from outpatient care into inpatient, diagnostics, dialysis, pharmacy, billing, and reporting workflows.

## Core Modules

- Patient registration and MPI
- Appointment and queue management
- Outpatient documentation
- Inpatient and ward management
- Emergency and triage
- Nursing documentation
- Vital signs and clinical monitoring
- Laboratory, imaging, pharmacy, billing, dialysis, and reporting integrations

## Design Principles

- Patient safety first
- Simple and usable interfaces
- Low-resource and offline-aware operation
- Future interoperability with national and clinical standards
- Role-based access and auditability

## Architecture Summary

- Django-based web application
- Role-aware dashboard and module-specific landing pages
- HTMX for partial updates
- Alpine.js for lightweight client-side interactions
- Chart.js for dashboard analytics

## Assumptions and Limitations

- The prototype uses synthetic or fictional patient data only.
- It is designed for hackathon submission and demonstration, not production deployment.
- Some interoperability, offline sync, and advanced governance features are represented as implementation-ready patterns rather than fully integrated external services.
- Final operational controls such as hosting hardening, backup policy enforcement, and institution-specific security operations are deployment responsibilities.
