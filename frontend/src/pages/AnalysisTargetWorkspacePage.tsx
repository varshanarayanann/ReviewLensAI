import { AppShell } from '../components/layout/AppShell'
import { AnalysisTargetWorkspaceView } from '../components/workspace/AnalysisTargetWorkspaceView'

export default function AnalysisTargetWorkspacePage() {
  return (
    <AppShell>
      <AnalysisTargetWorkspaceView state={{ kind: 'unavailable' }} />
    </AppShell>
  )
}
