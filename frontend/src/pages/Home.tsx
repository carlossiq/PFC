import { Navbar } from '../components/Navbar'
import { Sidebar } from '../components/Sidebar'
import { WorkflowPage } from '../components/Workflow'

export function Home() {
  return (
    <div className="min-h-screen">
      <Navbar />

      <div className="flex">
        <Sidebar />
        <WorkflowPage />
      </div>
    </div>
  )
}
