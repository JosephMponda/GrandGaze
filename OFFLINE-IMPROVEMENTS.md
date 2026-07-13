# OFFLINE PHASE 1 - Implementation Guide

## Goal
Make key clinical forms work offline and improve user feedback.

## Changes Required

### 1. static/js/app.js
- Strengthen offline form interception
- Reduce toast spam
- Ensure queue works reliably

### 2. Templates
- Add `data-offline-capable="true"` and `data-form-type` to critical forms

### 3. Base template
- Improve offline banner

## After Changes
- Hard refresh browser
- Test with network off


