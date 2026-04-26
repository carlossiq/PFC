# Frontend Menu Integration Guide

## Overview

O back-end fornece uma estrutura JSON completa do menu que o front-end pode consumir e renderizar. Tudo o que você precisa está em um único endpoint.

## API Endpoints

### 1. GET `/chat/menu` - Menu Completo

Retorna a estrutura hierárquica completa com todos os detalhes.

**Request:**
```bash
GET /chat/menu
```

**Response:**
```json
{
    "success": true,
    "data": {
        "version": "1.0.0",
        "menu": [
            {
                "id": "explore",
                "label": "Exploração Inicial",
                "icon": "compass",
                "description": "...",
                "items": [
                    {
                        "id": "refine_topic",
                        "label": "Refinar Tema",
                        "icon": "sparkles",
                        "endpoint": "POST /chat/refine-topic",
                        "inputs": {...},
                        "outputs": {...},
                        "duration": "~15-20s"
                    }
                ]
            }
        ],
        "workflow": {...},
        "features": {...}
    }
}
```

### 2. GET `/chat/menu/workflow` - Apenas Workflow

Retorna apenas os passos do fluxo recomendado.

**Response:**
```json
{
    "success": true,
    "data": {
        "recommended_flow": [
            {
                "step": 1,
                "action": "refine_topic",
                "description": "Começa com um tema genérico"
            },
            {
                "step": 2,
                "action": "build_probe_query",
                "description": "Escolhe um dos tópicos refinados"
            }
        ]
    }
}
```

## Frontend Implementation Examples

### React Example

#### 1. Fetch e Cache Menu

```typescript
// hooks/useMenu.ts
import { useEffect, useState } from 'react';

interface MenuSection {
  id: string;
  label: string;
  icon: string;
  description: string;
  items: MenuItem[];
}

interface MenuItem {
  id: string;
  label: string;
  icon: string;
  endpoint: string;
  description: string;
  inputs?: Record<string, any>;
  outputs?: Record<string, any>;
  duration?: string;
}

export function useMenu() {
  const [menu, setMenu] = useState<MenuSection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Check localStorage cache
    const cached = localStorage.getItem('menu_cache');
    if (cached) {
      setMenu(JSON.parse(cached));
      setLoading(false);
      return;
    }

    // Fetch from API
    fetch('/api/chat/menu')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setMenu(data.data.menu);
          // Cache for 1 hour
          localStorage.setItem('menu_cache', JSON.stringify(data.data.menu));
          localStorage.setItem('menu_cache_time', Date.now().toString());
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return { menu, loading, error };
}
```

#### 2. Render Menu (Sidebar)

```tsx
// components/Sidebar.tsx
import { useMenu } from '../hooks/useMenu';
import { Icon } from './Icon';

export function Sidebar() {
  const { menu, loading, error } = useMenu();

  if (loading) return <div>Loading menu...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <aside className="sidebar">
      {menu.map(section => (
        <div key={section.id} className="menu-section">
          <h2 className="section-header">
            <Icon name={section.icon} />
            {section.label}
          </h2>
          <p className="section-description">{section.description}</p>
          
          <ul className="menu-items">
            {section.items.map(item => (
              <li key={item.id} className="menu-item">
                <button
                  onClick={() => handleMenuItemClick(item)}
                  className="menu-button"
                >
                  <Icon name={item.icon} />
                  <div>
                    <span className="item-label">{item.label}</span>
                    <span className="item-duration">{item.duration}</span>
                  </div>
                </button>
                <p className="item-description">{item.description}</p>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </aside>
  );
}

function handleMenuItemClick(item: MenuItem) {
  // Show form/dialog based on item.inputs
  console.log('Calling:', item.endpoint);
  // Open DynamicForm with item.inputs
}
```

#### 3. Dynamic Form Builder

```tsx
// components/DynamicForm.tsx
interface DynamicFormProps {
  menuItem: MenuItem;
  onSubmit: (data: Record<string, any>) => void;
}

export function DynamicForm({ menuItem, onSubmit }: DynamicFormProps) {
  const [formData, setFormData] = useState<Record<string, any>>({});

  if (!menuItem.inputs) {
    return <p>No inputs required</p>;
  }

  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      onSubmit(formData);
    }}>
      <h3>{menuItem.label}</h3>
      <p>{menuItem.description}</p>

      {Object.entries(menuItem.inputs).map(([key, config]: [string, any]) => (
        <div key={key} className="form-group">
          <label htmlFor={key}>
            {config.label}
            {config.required && <span className="required">*</span>}
          </label>

          {config.type === 'string' && (
            <input
              id={key}
              type="text"
              placeholder={config.placeholder}
              value={formData[key] || ''}
              onChange={(e) => setFormData({
                ...formData,
                [key]: e.target.value
              })}
              required={config.required}
            />
          )}

          {config.type === 'enum' && (
            <select
              id={key}
              value={formData[key] || config.default}
              onChange={(e) => setFormData({
                ...formData,
                [key]: e.target.value
              })}
              required={config.required}
            >
              {config.options.map((opt: string) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          )}

          {config.type === 'number' && (
            <input
              id={key}
              type="number"
              min={config.min}
              max={config.max}
              value={formData[key] || config.default}
              onChange={(e) => setFormData({
                ...formData,
                [key]: parseInt(e.target.value)
              })}
              required={config.required}
            />
          )}

          {config.description && (
            <small>{config.description}</small>
          )}
        </div>
      ))}

      <div className="form-duration">
        Tempo estimado: {menuItem.duration}
      </div>

      <button type="submit" className="btn-primary">
        Executar
      </button>
    </form>
  );
}
```

#### 4. Workflow Stepper

```tsx
// components/WorkflowStepper.tsx
interface WorkflowStep {
  step: number;
  action: string;
  description: string;
}

export function WorkflowStepper() {
  const [workflow, setWorkflow] = useState<WorkflowStep[]>([]);
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    fetch('/api/chat/menu/workflow')
      .then(res => res.json())
      .then(data => setWorkflow(data.data.recommended_flow));
  }, []);

  return (
    <div className="workflow-stepper">
      {workflow.map((step, idx) => (
        <div
          key={step.step}
          className={`step ${idx <= currentStep ? 'active' : ''}`}
        >
          <div className="step-number">{step.step}</div>
          <div className="step-content">
            <h4>{step.action}</h4>
            <p>{step.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
```

### Vue Example

```vue
<!-- components/Menu.vue -->
<template>
  <aside class="sidebar">
    <div v-if="loading">Loading menu...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    
    <div v-for="section in menu" :key="section.id" class="menu-section">
      <h2 class="section-header">
        <i :class="`icon-${section.icon}`"></i>
        {{ section.label }}
      </h2>
      <p class="section-description">{{ section.description }}</p>
      
      <ul class="menu-items">
        <li v-for="item in section.items" :key="item.id" class="menu-item">
          <button
            @click="selectMenuItem(item)"
            class="menu-button"
          >
            <i :class="`icon-${item.icon}`"></i>
            <div>
              <span class="item-label">{{ item.label }}</span>
              <span v-if="item.duration" class="item-duration">
                {{ item.duration }}
              </span>
            </div>
          </button>
          <p class="item-description">{{ item.description }}</p>
        </li>
      </ul>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

const menu = ref([]);
const loading = ref(true);
const error = ref(null);

onMounted(async () => {
  try {
    const response = await fetch('/api/chat/menu');
    const data = await response.json();
    if (data.success) {
      menu.value = data.data.menu;
    }
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
});

function selectMenuItem(item) {
  console.log('Selected:', item.id);
  // Emit event or open dialog with form
}
</script>
```

## Data Structure Reference

### MenuItem Structure

```typescript
interface MenuItem {
  // Identification
  id: string;                          // Unique identifier
  label: string;                       // Display label
  icon: string;                        // Icon name (e.g., "sparkles", "compass")
  endpoint: string;                    // API endpoint (e.g., "POST /chat/refine-topic")
  
  // Documentation
  description: string;                 // What this action does
  duration?: string;                   // Estimated duration (e.g., "~15-20s")
  
  // Form Definition
  inputs?: {
    [key: string]: {
      type: string;                    // "string", "enum", "number", "InputIntake", "array"
      label: string;                   // Field label
      placeholder?: string;            // Placeholder text
      required: boolean;               // Is field required
      options?: string[];              // For enum type
      default?: any;                   // Default value
      min?: number;                    // For number type
      max?: number;                    // For number type
      description?: string;            // Help text
    }
  };
  
  // Response Documentation
  outputs?: {
    [key: string]: {
      type: string;                    // "array", "object", "string", etc.
      description: string;             // What this field contains
      fields?: string[];               // For object/array types
    }
  };
}
```

## Integration Checklist

- [ ] Fetch menu from `/chat/menu` on app load
- [ ] Cache menu in localStorage
- [ ] Render menu sections in sidebar
- [ ] Build dynamic forms from `item.inputs`
- [ ] Show estimated duration for each action
- [ ] Display workflow stepper
- [ ] Handle form submissions to API endpoints
- [ ] Show loading state during API calls
- [ ] Display results in structured view
- [ ] Link workflow steps (previous output → next input)
- [ ] Clear cache when needed

## Best Practices

1. **Caching**: Cache menu structure in localStorage to reduce API calls
2. **Progressive Disclosure**: Show form inputs only when needed
3. **User Guidance**: Display descriptions and estimated durations
4. **Error Handling**: Show clear error messages if API calls fail
5. **Input Validation**: Validate inputs before sending to API
6. **Result Display**: Show outputs in appropriate format (table, cards, etc.)
7. **Workflow State**: Track which step user is on
8. **Data Persistence**: Keep intermediate results for step-by-step workflow

## Example Complete Flow

```typescript
// Complete user journey
const user = {
  // Step 1: Load menu
  action: 'GET /chat/menu',
  result: 'Menu loaded with "Refinar Tema" action'
}

// Step 2: User clicks "Refinar Tema"
// Form shows inputs: { theme, description, area_of_study, keywords }

// Step 3: User submits form
const request1 = {
  endpoint: 'POST /chat/refine-topic',
  data: { theme: 'e-commerce', description: 'online retail' }
}
const result1 = '4 refined topics returned'

// Step 4: User selects one topic
// Menu shows next action: "Construir Query de Probe"

// Step 5: User clicks it
const request2 = {
  endpoint: 'POST /chat/probe/query',
  data: { intake: selectedTopic, api: 'ops' }
}
const result2 = 'Query structure returned'

// ... Continue through workflow ...
```

## Status: ✅ READY FOR FRONTEND

Menu structure is complete, documented, and ready for frontend consumption.
