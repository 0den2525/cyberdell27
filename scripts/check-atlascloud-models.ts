/**
 * Validates the static Atlas Cloud model lists against the live public catalog.
 * Usage: npm run check:atlascloud-models   (no API key needed; /v1/models is public)
 */
import { ATLAS_CLOUD_MODELS } from '../api/lib/ultraplinian'
import { ATLAS_CLOUD_MODELS as UI_MODELS } from '../src/components/ModelSelector'

async function main() {
  const res = await fetch('https://api.atlascloud.ai/v1/models')
  if (!res.ok) throw new Error(`GET /v1/models failed: HTTP ${res.status}`)
  const body = (await res.json()) as { data?: { id: string }[] }
  const live = new Set((body.data ?? []).map(m => m.id))

  const configured = new Set<string>()
  Object.values(ATLAS_CLOUD_MODELS).forEach(list => list.forEach(id => configured.add(id)))
  UI_MODELS.forEach(m => configured.add(m.id))
  const missing = Array.from(configured).filter(id => !live.has(id))

  console.log(`${configured.size} configured Atlas Cloud models, ${live.size} in live catalog`)
  if (missing.length > 0) {
    console.error(`Missing from live catalog: ${missing.join(', ')}`)
    process.exit(1)
  }
  console.log('All configured model ids are present.')
}

main().catch(err => { console.error(err); process.exit(1) })
