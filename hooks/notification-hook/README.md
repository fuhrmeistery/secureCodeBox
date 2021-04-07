---
title: "Notification Hook"
category: "hook"
type: "integration"
state: "roadmap"
usecase: "Publishes Scan Summary to MS Teams, Slack and others."
---

<!-- end -->

## Deployment

Installing the Notification hook will add a ReadOnly Hook to your namespace.

> 🔧 The implementation is currently work-in-progress and still undergoing major changes. It'll be released here once it has stabilized.

```bash
helm upgrade --install nwh ./hooks/notification-hook/ --set notification.url="http://example.com/my/hook/target"
```

> ✍ This documentation is currently work-in-progress.