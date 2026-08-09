/**
 * magmascript JavaScript client — for web dashboard and Node.js scripts
 *
 * Usage:
 *   import { MCPClient } from './lib/magmascript.js'
 *
 *   const client = new MCPClient()
 *   const results = await client.search('aphex twin')
 *   const boards = await client.scoreboards()
 */

const DEFAULT_URL = 'https://magmacrunch.duckdns.org/mcp'

class RPCError extends Error {
  constructor(code, message, data) {
    super(`RPC error ${code}: ${message}`)
    this.code = code
    this.data = data
  }
}

class RPCClient {
  constructor(url, apiKey) {
    this.url = url || DEFAULT_URL
    this.apiKey = apiKey || ''
    this.id = 0
    this.initialized = false
  }

  _headers() {
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json, text/event-stream',
      'Authorization': `Bearer ${this.apiKey}`,
    }
  }

  async call(method, params) {
    const msg = { jsonrpc: '2.0', id: ++this.id, method }
    if (params) msg.params = params

    const resp = await fetch(this.url, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify(msg),
    })

    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`)

    const contentType = resp.headers.get('content-type') || ''

    if (contentType.includes('text/event-stream')) {
      return this._parseSSE(await resp.text())
    }

    const data = await resp.json()
    if (data.error) throw new RPCError(data.error.code, data.error.message, data.error.data)
    return data.result
  }

  _parseSSE(text) {
    let lastResult = null
    for (const line of text.split('\n')) {
      if (!line.startsWith('data: ')) continue
      const payload = line.slice(6).trim()
      if (!payload) continue
      try {
        const data = JSON.parse(payload)
        if (data.error) throw new RPCError(data.error.code, data.error.message, data.error.data)
        if (data.result) lastResult = data.result
      } catch (e) {
        if (e instanceof RPCError) throw e
      }
    }
    return lastResult
  }

  async initialize() {
    const result = await this.call('initialize', {
      protocolVersion: '2025-11-25',
      capabilities: {},
      clientInfo: { name: 'magmascript-js', version: '1.0.0' },
    })
    await this.call('notifications/initialized', {})
    this.initialized = true
    return result
  }

  async callTool(name, args) {
    if (!this.initialized) await this.initialize()
    const result = await this.call('tools/call', { name, arguments: args || {} })
    if (result?.isError) {
      const text = result.content?.[0]?.text || 'Unknown error'
      throw new Error(text)
    }
    return result?.content?.[0]?.text || JSON.stringify(result)
  }

  async listTools() {
    if (!this.initialized) await this.initialize()
    const result = await this.call('tools/list', {})
    return result?.tools || []
  }
}

class MCPClient {
  constructor(url, apiKey) {
    this.rpc = new RPCClient(url, apiKey)
  }

  // MusicBrainz Cache
  async search(query) { return this.rpc.callTool('search_cache', { query }) }
  async listEntities(type) { return this.rpc.callTool('list_cached_entities', type ? { entity_type: type } : {}) }
  async getEntity(type, key) { return this.rpc.callTool('get_entity', { entity_type: type, key }) }

  // High Scores
  async scoreboards() { return this.rpc.callTool('list_scoreboards') }
  async scores(game, limit) { return this.rpc.callTool('get_scores', { game, limit: limit || 10 }) }

  // Project Structure
  async archivePages() { return this.rpc.callTool('list_archive_pages') }
  async arcadeGames() { return this.rpc.callTool('list_arcade_games') }

  // Pi Services
  async piStatus() { return this.rpc.callTool('check_pi_services') }
  async piLogs(service, lines) { return this.rpc.callTool('get_service_logs', { service, lines_count: lines || 30 }) }
  async piRestart(service) { return this.rpc.call_tool('restart_pi_service', { service }) }
  async piInfo() { return this.rpc.callTool('get_pi_system_info') }

  // Deployment
  async deploy(path, service) {
    const args = { local_path: path }
    if (service) args.service = service
    return this.rpc.callTool('deploy_to_pi', args)
  }

  // GitHub Bots
  async bots() { return this.rpc.callTool('list_bots') }
  async botStatus(name) { return this.rpc.callTool('get_bot_status', { workflow_name: name }) }
  async triggerBot(name) { return this.rpc.callTool('trigger_bot', { workflow_name: name }) }
  async botRuns(name, limit) { return this.rpc.callTool('get_bot_runs', { workflow_name: name, limit: limit || 10 }) }

  // Discogs
  async discogsSearch(query, type) { return this.rpc.callTool('search_discogs', { query, search_type: type || 'release' }) }
  async discogsRelease(id) { return this.rpc.callTool('get_discogs_release', { release_id: id }) }
  async discogsArtist(id) { return this.rpc.callTool('get_discogs_artist', { artist_id: id }) }
  async discogsLabel(id) { return this.rpc.callTool('get_discogs_label', { label_id: id }) }

  // Admin Data
  async jukeboxSongs() { return this.rpc.callTool('get_jukebox_songs') }
  async tvChannels() { return this.rpc.callTool('get_tv_channels') }
  async themes() { return this.rpc.callTool('get_themes') }
  async playCounts() { return this.rpc.callTool('get_play_counts') }
  async artistPlayCounts(name) { return this.rpc.callTool('get_artist_play_counts', { artist_name: name }) }
}

// Node.js module exports
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { MCPClient, RPCClient, RPCError }
}

// ES module exports
export { MCPClient, RPCClient, RPCError }
