# Vercel + Render Deployment: Quick Reference Guide

Quick answers to common deployment scenarios and issues.

---

## Quick Decision Trees

### "My Frontend Can't Connect to My Backend"

```
START: Frontend can't connect to backend
│
├─ Is this development (localhost)?
│  ├─ YES → Add http://localhost:5000 to CORS origins on backend
│  └─ NO → Continue...
│
├─ Check browser console for CORS error
│  ├─ "Access-Control-Allow-Origin header missing"
│  │  └─ → Add CORS headers to Render backend (Section 3.3)
│  │
│  ├─ "Cannot connect to server"
│  │  └─ → Is Render backend running? Check Render dashboard
│  │     → Add health check pings to keep backend active
│  │     → Check NEXT_PUBLIC_API_URL is correct
│  │
│  └─ "Error: Network request failed"
│     └─ → Try adding retry logic (Section: Error Handling)
│        → Check firewall/network settings
│        → Verify HTTPS certificate is valid
│
└─ Still not working?
   └─ → Check Vercel logs: Deployments → Select deployment
      → Check Network tab in browser DevTools
      → Use curl to test backend directly
```

### "My Environment Variables Aren't Working"

```
START: Environment variables not working
│
├─ Are they accessible in the code?
│  ├─ undefined in browser?
│  │  └─ → Must use NEXT_PUBLIC_ prefix (Section 2.3)
│  │     → Redeploy after adding variable
│  │
│  ├─ undefined on server/API route?
│  │  └─ → Variable not set in Vercel dashboard
│  │     → Check correct environment: Production vs Preview
│  │     → Use vercel env list to verify
│  │
│  └─ Correct in development but not production?
│     └─ → Verify variable set in PRODUCTION environment
│        → Check branch-specific overrides aren't preventing it
│
├─ Check environment variable scope
│  ├─ SET in Production only?
│  │  └─ → Won't appear in Preview/staging deployments
│  │
│  ├─ SET as branch-specific?
│  │  └─ → Only applies to that specific branch
│  │
│  └─ Recent changes?
│     └─ → Redeploy project for variables to take effect
│
└─ Still not working?
   └─ → Delete variable and re-add it
      → Check for typos in variable name
      → Check character limits not exceeded (64KB total)
```

### "My Build is Failing"

```
START: Build is failing on Vercel
│
├─ Check build error message
│  ├─ "Module not found"
│  │  └─ → Missing dependency in package.json
│  │     → Run npm install locally
│  │     → Check package versions match
│  │
│  ├─ "Cannot find module '@/components/X'"
│  │  └─ → TypeScript path alias not configured
│  │     → Check tsconfig.json/jsconfig.json
│  │
│  ├─ "Build failed with exit code 1"
│  │  └─ → General build error
│  │     → Run npm run build locally to see full error
│  │
│  ├─ "Exceeded maximum build duration"
│  │  └─ → Build taking too long
│  │     → Remove heavy dependencies
│  │     → Enable caching
│  │     → Split build into smaller chunks
│  │
│  └─ "Failed to download Next.js"
│     └─ → Network issue during build
│        → Click "Redeploy" to retry
│        → Check package versions
│
├─ Test build locally
│  ├─ npm run build
│  ├─ npm run lint
│  ├─ npm run type-check
│  └─ Fix any errors
│
└─ Still failing?
   └─ → Check .vercelignore isn't excluding required files
      → Clear Vercel cache: Settings → Git → Redeploy
      → Check for environment variable issues at build time
      → Use vercel build locally for more details
```

### "My Custom Domain Isn't Working"

```
START: Custom domain issues
│
├─ Can you access site via .vercel.app domain?
│  ├─ NO → Site not deployed properly
│  │     → Check Deployments tab for errors
│  │     → Re-deploy to fix
│  │
│  └─ YES → Continue...
│
├─ Has DNS propagated?
│  ├─ Use nameservers (Vercel DNS)
│  │  └─ → Changed nameservers at registrar?
│  │     → Waiting up to 48 hours for propagation?
│  │     → Verify correct nameservers added:
│  │        ns1.vercel-dns.com
│  │        ns2.vercel-dns.com
│  │        ns3.vercel-dns.com
│  │        ns4.vercel-dns.com
│  │
│  └─ Using DNS records (non-Vercel DNS)
│     └─ → Added A record for @ → 76.76.21.21?
│        → Added CNAME for www → cname.vercel-dns.com?
│        → Check registrar DNS management
│
├─ Is SSL certificate generated?
│  ├─ Showing "Generating SSL Certificate"?
│  │  └─ → Wait 5-10 minutes
│  │     → Check Vercel logs
│  │     → May take longer if DNS just changed
│  │
│  ├─ Certificate failed to generate?
│  │  └─ → Check CAA record allows Let's Encrypt
│  │     → Remove Cloudflare proxy if using (conflicts with cert validation)
│  │     → Verify DNS is fully set up
│  │
│  └─ Certificate issued successfully?
│     └─ → Should be accessible via HTTPS
│        → Wait for DNS cache to clear (usually <1hr)
│
└─ Still having issues?
   └─ → Domain resolves but shows error?
      → Use https://dns.google or mxtoolbox to check DNS
      → Force refresh browser (Ctrl+Shift+R)
      → Check if domain is used elsewhere
```

---

## Common Issues & Quick Fixes

### Issue: First Request to Render Backend Fails

**Symptom**: First API call after inactivity returns connection error, but subsequent calls work.

**Root Cause**: Render spins down free tier instances after 15 minutes of inactivity.

**Solutions** (in order of recommendation):

1. **Implement Health Check Pings**
   ```javascript
   // Schedule pings using UptimeRobot (free) or similar
   // Pings should hit https://your-api.onrender.com/api/health every 5 minutes
   // This keeps the instance warm and running
   ```

2. **Add Retry Logic on Frontend**
   ```javascript
   const response = await fetchWithRetry(
     `${apiUrl}/api/endpoint`,
     { maxRetries: 3, baseDelay: 1000 }
   );
   ```

3. **Upgrade Render Plan**
   - Paid instances never spin down
   - Provides better reliability for production

### Issue: CORS Error in Production but Not Localhost

**Symptom**: Works on localhost, but "CORS error" on production.

**Root Cause**: CORS origins configured for specific domains, not wildcard.

**Fix**:
```javascript
// On Render backend
const corsOptions = {
  origin: [
    'https://your-app.vercel.app',
    'http://localhost:3000' // for dev only
  ]
};
```

**Debug Checklist**:
- [ ] Vercel domain exactly matches CORS origin
- [ ] Using https:// not http://
- [ ] No trailing slash
- [ ] No extra whitespace
- [ ] Backend deployed after CORS config change

### Issue: Environment Variables Show as Undefined

**Symptom**: `console.log(process.env.API_URL)` shows undefined

**Checklist**:
- [ ] Variable added in Vercel Project Settings?
- [ ] Correct environment selected (Production/Preview)?
- [ ] Project redeployed after adding variable?
- [ ] For client-side: Does it have `NEXT_PUBLIC_` prefix?
- [ ] No typos in variable name?

**Debug Steps**:
```bash
# List all environment variables
vercel env list

# Pull environment variables locally
vercel env pull

# Check .env file was created
cat .env
```

### Issue: API Route Returns 404

**Symptom**: `/api/users` returns 404 Not Found

**Checklist**:
- [ ] File exists at correct path?
  - Pages Router: `pages/api/users.js`
  - App Router: `app/api/users/route.ts`
- [ ] File exported correct function?
  - Pages Router: `export default function handler(req, res)`
  - App Router: `export async function GET(request)`
- [ ] Correct HTTP method?
  - Pages Router: checks `req.method`
  - App Router: function name matches method (GET, POST, etc.)
- [ ] No syntax errors in file?
  - Run `npm run build` locally to check

**Fix**:
```typescript
// Correct App Router structure
export async function GET(request: Request) {
  return Response.json({ data: [] });
}

export async function POST(request: Request) {
  const body = await request.json();
  return Response.json({ created: true });
}
```

### Issue: Build Timeout (504 Function Timeout)

**Symptom**: Function execution exceeds timeout, returns 504 Gateway Timeout

**Default Timeouts**:
- Hobby plan: 10 seconds
- Pro plan: 60 seconds (default 15 seconds)
- Enterprise: 900 seconds (15 minutes)

**Solutions**:
1. **For Next.js** - Configure in `next.config.js`:
   ```javascript
   const nextConfig = {
     functions: {
       'pages/api/**/*': { maxDuration: 60 }
     }
   };
   ```

2. **For App Router** - Add to `route.ts`:
   ```typescript
   export const maxDuration = 60; // seconds
   ```

3. **Optimize function**:
   - Remove heavy operations
   - Use pagination for large datasets
   - Add caching
   - Consider background jobs

4. **Enable Fluid Compute** (Pro/Enterprise):
   - Project Settings → Functions
   - Allows up to 800 seconds

### Issue: High Build Costs

**Symptom**: Vercel billing unexpectedly high

**Common Causes**:
- Image optimization running too often
- Unnecessary API calls during build
- Large dependencies
- ISR revalidating too frequently

**Solutions**:
```javascript
// next.config.js
module.exports = {
  images: {
    unoptimized: true // for static export, if needed
  },

  // Limit ISR revalidation
  revalidate: 3600 // 1 hour instead of 60 seconds
};
```

---

## Environment Variable Reference

### Frontend Variables (Client-Side)

Must have `NEXT_PUBLIC_` prefix to be accessible in browser.

```env
# API Configuration
NEXT_PUBLIC_API_URL=https://api.example.com

# Feature Flags
NEXT_PUBLIC_FEATURE_BETA=false
NEXT_PUBLIC_FEATURE_NEW_UI=true

# Analytics & Monitoring
NEXT_PUBLIC_GOOGLE_ANALYTICS_ID=G-xxx
NEXT_PUBLIC_SENTRY_DSN=https://key@sentry.io/xxx

# Third-party API Keys (Public)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_xxx
NEXT_PUBLIC_MAPBOX_TOKEN=pk_xxx
```

### Backend Variables (Server-Side Only)

These should NOT have `NEXT_PUBLIC_` prefix - they're not exposed to browser.

```env
# Secrets
API_SECRET=secret-key-here
JWT_SECRET=jwt-secret-key
SESSION_SECRET=session-secret

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
DATABASE_POOL_MIN=2
DATABASE_POOL_MAX=10

# Third-party Secret Keys
STRIPE_SECRET_KEY=sk_live_xxx
SENDGRID_API_KEY=SG.xxx
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

### System Variables Available on Vercel

These are automatically provided by Vercel:

```env
# Deployment Information
VERCEL=1
VERCEL_ENV=production|preview|development
VERCEL_URL=your-app.vercel.app
VERCEL_GIT_COMMIT_SHA=abc123...
VERCEL_GIT_COMMIT_MESSAGE=Commit message
VERCEL_GIT_BRANCH=main
VERCEL_GIT_REPO_ID=123456
VERCEL_GIT_REPO_OWNER=username
VERCEL_GIT_REPO_SLUG=repo-name
VERCEL_GIT_PULL_REQUEST_ID=42
```

---

## Deployment Command Reference

### Deploy Manually (Without GitHub)

```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel account
vercel login

# Navigate to project directory
cd your-project

# First time: link project
vercel link

# Deploy to preview (staging URL)
vercel

# Deploy to production (main domain)
vercel --prod

# Deploy with specific environment variables
vercel --prod --env DATABASE_URL=xyz --env API_KEY=abc

# Force redeploy of specific deployment
vercel rollback

# See deployment history
vercel list
```

### Using Vercel CLI for Environment Management

```bash
# Pull all environment variables
vercel env pull

# This creates .env file - add to .gitignore!

# List environment variables
vercel env list

# Add new environment variable
vercel env add MY_VAR

# Remove environment variable
vercel env rm MY_VAR

# View project configuration
vercel info

# Check project status
vercel status
```

---

## Performance Checklist

### Before Every Production Deploy

- [ ] Run `npm run build` locally - completes without errors
- [ ] Run `npm run lint` - no warnings
- [ ] Run `npm run type-check` - no type errors
- [ ] Run `npm test` - all tests passing
- [ ] Bundle size acceptable (< 200KB gzipped recommended)
- [ ] Lighthouse score > 90
- [ ] Core Web Vitals:
  - LCP < 2.5s
  - INP < 200ms
  - CLS < 0.1

### After Every Production Deploy

- [ ] Site loads without errors
- [ ] Core functionality works
- [ ] No 404 errors
- [ ] API calls returning data
- [ ] Check Vercel Analytics for metrics
- [ ] Monitor error tracking for new issues

### Performance Optimization Priorities

1. **Critical (Do First)**
   - Enable image optimization
   - Code splitting for large components
   - Minify JavaScript and CSS
   - Use HTTP caching headers

2. **Important (Do Soon)**
   - Set up performance monitoring
   - Optimize database queries
   - Implement pagination for large lists
   - Reduce bundle size

3. **Nice to Have (When Time Available)**
   - Edge functions for geolocation
   - Advanced caching strategies
   - Service workers for offline support
   - Advanced analytics

---

## Security Checklist

### Before Production Launch

- [ ] HTTPS enabled and working
- [ ] Security headers configured:
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: SAMEORIGIN
  - Strict-Transport-Security
- [ ] CORS properly configured (not using wildcard)
- [ ] Environment variables not logged
- [ ] No secrets in code or version control
- [ ] Rate limiting configured on API
- [ ] Authentication/authorization working
- [ ] SQL injection protection verified
- [ ] XSS protection in place
- [ ] CSRF tokens implemented
- [ ] Two-factor authentication for admin accounts
- [ ] Deployment protection enabled
- [ ] Error tracking configured (Sentry, etc.)
- [ ] Web Application Firewall (WAF) enabled if available

### Regular Security Maintenance

- [ ] Run `npm audit` weekly
- [ ] Update dependencies monthly
- [ ] Review access logs for suspicious activity
- [ ] Rotate secrets quarterly
- [ ] Review team member access
- [ ] Check SSL certificate expiration (Vercel handles this, but verify)

---

## Vercel Settings Quick Reference

### Project Settings

Location: Project Settings in Vercel Dashboard

**Git** Section:
- Deploy on commit: ✓ (usually enabled)
- Redeploy: Forces rebuild
- Clone private repos: Enable if using private packages

**Domains** Section:
- Add custom domains
- Configure SSL certificates
- Set up DNS records

**Environment Variables** Section:
- Add variables for Production, Preview, Development
- Create branch-specific overrides
- Manage sensitive values

**Functions** Section:
- Set max duration for API routes
- Configure memory allocation
- Set regions for deployment

**Integrations** Section:
- Connect GitHub/GitLab
- Enable analytics
- Configure monitoring
- Connect Slack notifications

### Team Settings

Location: Team Settings in Vercel Dashboard

**Members** Section:
- Invite team members
- Manage permissions
- Enable two-factor authentication

**Billing** Section:
- View usage and costs
- Manage payment method
- Set spending limits

**API Tokens** Section:
- Generate personal tokens for CI/CD
- Manage token permissions
- Revoke compromised tokens

---

## DNS Record Examples

### Using Vercel Nameservers (Recommended)

At your registrar, set nameservers to:
```
ns1.vercel-dns.com
ns2.vercel-dns.com
ns3.vercel-dns.com
ns4.vercel-dns.com
```

Then manage all DNS in Vercel dashboard.

### Using External DNS Provider

Add these records at your DNS provider:

**For Root Domain (example.com)**
```
Type: A
Name: @
Value: 76.76.21.21
TTL: 3600
```

**For WWW Subdomain (www.example.com)**
```
Type: CNAME
Name: www
Value: cname.vercel-dns.com
TTL: 3600
```

**For Custom Subdomain (api.example.com)**
```
Type: CNAME
Name: api
Value: cname.vercel-dns.com
TTL: 3600
```

**For Email (if using Gmail/Office365 etc)**
```
Type: MX
Name: @
Value: mx.google.com (for Gmail)
Priority: 5
TTL: 3600
```

**Verify HTTPS Support**
```
Type: CAA
Name: @
Value: 0 issue "letsencrypt.org"
TTL: 3600
```

---

## Monitoring & Alerting Setup

### Key Metrics to Monitor

**Application Metrics**:
- Error rate (target: < 0.1%)
- API response time (target: p95 < 1s)
- Function execution time (target: avg < 200ms)

**User Experience Metrics**:
- Core Web Vitals (LCP, INP, CLS)
- Page load time
- Time to Interactive

**Infrastructure Metrics**:
- Deployment frequency
- Deployment success rate
- Rollback frequency
- Function cold starts

### Alert Thresholds

```
High Priority (Page Immediately):
- Error rate > 1%
- API response time > 2 seconds
- Service completely down

Medium Priority (Within 1 Hour):
- Error rate > 0.5%
- API response time > 1 second
- Performance degradation > 20%

Low Priority (Daily Summary):
- New minor errors appeared
- Deployment statistics
```

---

## Quick Troubleshooting Commands

```bash
# Check what Vercel CLI has linked
vercel status

# See recent deployments
vercel list

# View a specific deployment's logs
vercel logs [deployment-url]

# Pull environment variables for local testing
vercel env pull

# Test your build command locally
vercel build

# Run Vercel CLI in debug mode for more info
vercel deploy --debug

# Check project info
vercel info

# List all linked projects
vercel projects list
```

---

## Useful Links

### Official Documentation
- Vercel Docs: https://vercel.com/docs
- Production Checklist: https://vercel.com/docs/production-checklist
- Environment Variables: https://vercel.com/docs/environment-variables
- Error Codes: https://vercel.com/docs/errors

### Community & Support
- Vercel Community: https://community.vercel.com
- GitHub Issues: https://github.com/vercel/vercel/issues
- Stack Overflow: [vercel] tag

### Related Services
- Render: https://render.com
- Stripe (Payments): https://stripe.com
- Sentry (Error Tracking): https://sentry.io
- PostHog (Analytics): https://posthog.com

---

## Summary

This quick reference guide covers:
- Common deployment issues and solutions
- Environment variable configuration
- Command-line tools and shortcuts
- Security and performance checklists
- DNS and domain configuration
- Monitoring and alerting setup

For detailed information, refer to the main `VERCEL_DEPLOYMENT_GUIDE.md` document.

**Last Updated**: November 2024
**Status**: Production Ready
