-- MIT License. Visible information only. No deck contents, RNG or save access.
local function json(v, seen)
    local t = type(v)
    if t == 'nil' then return 'null' end
    if t == 'boolean' then return tostring(v) end
    if t == 'number' then
        if v ~= v or v == math.huge or v == -math.huge then return 'null' end
        return tostring(v)
    end
    if t == 'string' then
        return '"' .. v:gsub('[%z\1-\31\\"]', function(c)
            if c == '"' then return '\\"' end
            if c == '\\' then return '\\\\' end
            return string.format('\\u%04x', string.byte(c))
        end) .. '"'
    end
    if t ~= 'table' then return 'null' end
    seen = seen or {}
    if seen[v] then return 'null' end
    seen[v] = true
    local out = {}
    local array = #v > 0 or next(v) == nil
    if array then
        for i=1,#v do out[#out+1] = json(v[i],seen) end
    else
        for k,val in pairs(v) do out[#out+1] = json(tostring(k)) .. ':' .. json(val,seen) end
    end
    seen[v] = nil
    return (array and '[' or '{') .. table.concat(out,',') .. (array and ']' or '}')
end

local function visible(card)
    if card.facing == 'back' then return {hidden=true} end
    local center = card.config and card.config.center or {}
    local name = center.name or center.key or ''
    if localize and center.key then
        local ok, n = pcall(localize,{type='name_text',set=center.set or 'Joker',key=center.key})
        if ok and type(n)=='string' then name=n end
    end
    return {
        key=center.key, name=name, rank=card.base and card.base.id,
        suit=card.base and card.base.suit, enhancement=center.key,
        debuff=card.debuff or false, cost=tonumber(card.cost) or 0,
        seal=card.seal, edition=card.edition and card.edition.key
    }
end

local function area(a)
    local out={}
    for _,c in ipairs(a and a.cards or {}) do out[#out+1]=visible(c) end
    return out
end

local function finite(n)
    -- Big-number mods are deliberately not treated as normal score values.
    return type(n)=='number' and n==n and n~=math.huge and n~=-math.huge and n or 0
end

local elapsed = 0
local original = Game.update
function Game:update(dt)
    local result = original(self,dt)
    elapsed = elapsed + dt
    if elapsed < 0.5 then return result end
    elapsed = 0
    local ok, err = pcall(function()
        local game=G.GAME or {}
        local round=game.current_round or {}
        local blind=game.blind or {}
        local selected={}
        for _,c in ipairs(G.hand and G.hand.highlighted or {}) do selected[#selected+1]=visible(c) end
        local state={
            schema=1,timestamp=os.time(),game_version=G.VERSION,
            in_run=G.STAGE==G.STAGES.RUN,state=G.STATE,
            ante=finite(game.round_resets and game.round_resets.ante),
            money=finite(game.dollars),hands=finite(round.hands_left),discards=finite(round.discards_left),
            chips=finite(game.chips),target=finite(blind.chips),
            blind={key=blind.config and blind.config.blind and blind.config.blind.key or '',name=blind.name or '',disabled=blind.disabled or false},
            jokers=area(G.jokers),hand=area(G.hand),shop=area(G.shop_jokers),selected=selected,
            joker_limit=G.jokers and G.jokers.config.card_limit or 5
        }
        local payload=json(state)
        local root=love.filesystem.getSaveDirectory()
        local tmp=root..'/balatro_coach_state.tmp'
        local target=root..'/balatro_coach_state.json'
        local file=assert(io.open(tmp,'wb'))
        file:write(payload);file:close()
        -- Windows rename cannot replace existing files. Reader retries on a gap.
        os.remove(target)
        assert(os.rename(tmp,target))
    end)
    if not ok and sendWarnMessage then sendWarnMessage(tostring(err),'BalatroCoachBridge') end
    return result
end
