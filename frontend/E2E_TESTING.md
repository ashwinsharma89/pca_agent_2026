# E2E Testing with Playwright

We use Playwright for our end-to-end testing suite to ensure that the frontend remains functional across all critical user flows.

## Test Configuration

- **Base URL:** `http://localhost:3000`
- **Browsers:** Chromium, Firefox, WebKit
- **Viewports:** Desktop, Pixel 5 (Mobile), iPhone 12 (Mobile Safari)
- **Wait Policy:** We use `waitForURL` and `expect(locator).toBeVisible()` to handle asynchronous updates.

## Core Test Suite

The primary test suite is located in `e2e/core-flows.spec.ts`. This suite covers:

1.  **Authentication:** Validates login with `ashwin` / `Pca12345!` and handles error cases.
2.  **Navigation:** Ensures all major modules are accessible and display correctly:
    - Dashboard
    - Upload
    - Intelligence Studio
3.  **Intelligence Studio:** Validates that the AI Chat interface accepts input and shows loading states.

## Running Tests

From the `frontend` directory:

```bash
# Run all core tests
npx playwright test e2e/core-flows.spec.ts

# Run with UI mode (best for debugging)
npx playwright test --ui

# Run only on Chromium (fastest)
npx playwright test e2e/core-flows.spec.ts --project=chromium

# View the last test report
npx playwright show-report
```

## Credential Management

The tests use the standard `ashwin` account. If you need to change the credentials used for testing, update the `TEST_USER` constant in `e2e/core-flows.spec.ts`:

```typescript
const TEST_USER = {
    username: 'ashwin',
    password: 'Pca12345!'
};
```

## Adding New Tests

When adding new pages to the PCA Agent:
1.  Add a navigation test to verify the route is accessible.
2.  Add a basic interaction test (e.g., clicking a button or checking for an H1).
3.  Ensure you use robust selectors like `role` or `id` where possible.
