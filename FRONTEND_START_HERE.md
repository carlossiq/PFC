# Start Here - AGIA Frontend

## You're 3 Commands Away From Running

```bash
# 1. Go to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```

**Done!** The app will be at: http://localhost:5173

---

## What You'll See

A professional interface with:
- **Left**: Dark blue sidebar with configuration options
- **Top**: Workflow stepper showing 4 steps
- **Center**: Main working area that changes based on the current step
- **Right** (sometimes): Results panel or PDF preview

## 4-Step Workflow

1. **Configuration** - Set theme, keywords, sources, and date range
2. **Query Generation** - Review and edit auto-generated search query
3. **Curation** - Accept/reject search results
4. **LaTeX Report** - Edit and compile technical report to PDF

## Try These Actions

### Step 1: Configuration
- Type a theme (e.g., "Machine Learning")
- Add keywords (e.g., "AI", "Healthcare")
- Click "Salvar Configurações" (Save Configuration)
- Click the blue step 2 button or "Next: Generate Query"

### Step 2: Query Generation
- See an auto-generated search query in CQL syntax
- Review the 3 mock search results on the right panel
- Click "Accept" or "Discard" on each result
- Click "Confirm and Continue"

### Step 3: Curation
- Review the selected results
- Click "Next: Generate Report LaTeX"

### Step 4: LaTeX Report
- See a Monaco Editor on the left with a sample LaTeX document
- See file tree on the left (main.tex, references.bib, figures/)
- Edit the LaTeX text
- Click "Compile" to generate PDF (simulated)
- Click "Download PDF" to save

## Commands

```bash
# Development (auto-reload)
npm run dev

# Production build
npm run build

# Preview the build
npm run preview

# Type checking
npm run type-check

# Linting
npm run lint
```

## File Locations

- **Frontend root**: `/frontend`
- **Components**: `/frontend/src/components/`
- **Services**: `/frontend/src/services/`
- **Types**: `/frontend/src/types/`
- **Main app**: `/frontend/src/App.tsx`

## Documentation

- **Quick Start** (5 min): See `FRONTEND_QUICK_START.md`
- **Complete Setup** (15 min): See `FRONTEND_SETUP.md`
- **Technical Details**: See `FRONTEND_COMPLETE.md`

## Common Questions

### Where's the backend?
Currently, the app uses mock data for demonstration. The API service is ready to connect to a real backend.

### How do I connect the backend?
1. Create the 11 API endpoints in your FastAPI app
2. Uncomment the real API calls in `src/App.tsx`
3. Update `.env` with your backend URL
4. Test the integration

### Can I modify it?
Yes! It's all TypeScript and React. Edit components in `/src/components/`, add styles with TailwindCSS, and customize types in `/src/types/`.

### How do I deploy?
```bash
# Build for production
npm run build

# Then either:
# - Deploy the 'dist' folder to Vercel, Netlify, etc.
# - Containerize with Docker
# - Or use your preferred hosting
```

## Need Help?

1. Check the docs: `FRONTEND_QUICK_START.md`
2. Review the code: It's well-commented
3. Check the browser console for errors
4. Verify backend is running if you enabled API integration

## What's Included

- ✅ 6 fully functional React components
- ✅ Axios HTTP client configured
- ✅ Monaco Editor for LaTeX editing
- ✅ TailwindCSS for styling
- ✅ TypeScript for type safety
- ✅ Hot Module Reload (HMR)
- ✅ Production-ready build
- ✅ Mock data for testing
- ✅ 100% responsive design

## Go Build Something Amazing!

You now have a professional frontend ready for your backend. Happy coding!

---

**Stack**: React 18 + Vite + TypeScript + TailwindCSS  
**Status**: Ready to use  
**Date**: 2026-04-28
