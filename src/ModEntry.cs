/*

The Stardew Parable - Stardew Valley narrado por IA
Esse é um projeto feito por @keyditor

Utilize com bom senso.


*/

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using System.Text;
using System.Text.Json;
using StardewModdingAPI;
using StardewModdingAPI.Events;
using StardewModdingAPI.Utilities;
using StardewValley;
using StardewValley.Menus;
using StardewValley.TerrainFeatures;
using StardewValley.Locations;
using StardewValley.Monsters;

namespace ActionLogger
{
    public class ModConfig
    {
        public string BackendUrl { get; set; } = "http://localhost:8000/actions";
        public string TtsApiUrl { get; set; } = "http://localhost:8000/tts";
        public string NarrationMode { get; set; } = "Diaria";
        public string OpenAiUrl { get; set; } = "";
        public string OpenAiApiKey { get; set; } = "";
        public string OpenAiModel { get; set; } = "";
        public string GeminiApiKey { get; set; } = "";
        public string GeminiModel { get; set; } = "";
        public string GeminiApiBase { get; set; } = "";
        public bool UseGemini { get; set; } = false;
        public string ElevenLabsApiKey { get; set; } = "";
        public string ElevenLabsVoiceId { get; set; } = "";
    }

    public interface IGenericModConfigMenuApi
    {
        void Register(IManifest mod, Action reset, Action save, bool titleScreenOnly = false);
        void AddTextOption(IManifest mod, Func<string> getValue, Action<string> setValue, Func<string> name, Func<string> tooltip = null, string[] allowedValues = null, Func<string, string> formatAllowedValue = null, string fieldId = null);
        void AddBoolOption(IManifest mod, Func<bool> getValue, Action<bool> setValue, Func<string> name, Func<string> tooltip = null, string fieldId = null);
    }

    public class ModEntry : Mod
    {
        private ModConfig Config;

        private class ActionLog
        {
            public string BaseMessage { get; set; }
            public string ToolName { get; set; }
            public int InGameTime { get; set; }
            public int Count { get; set; }
            public string PlayerName { get; set; }
            public string LocationName { get; set; }

            public ActionLog(string baseMessage, string toolName, int timeChunk)
            {
                BaseMessage = baseMessage;
                ToolName = toolName;
                InGameTime = timeChunk;
                PlayerName = Game1.player?.Name ?? "Nenhum";
                LocationName = GetLocationName(Game1.currentLocation);
                Count = 1;
            }

            public string GetFormattedString()
            {
                string timeStr = Game1.getTimeOfDayString(InGameTime);
                string countStr = Count > 1 ? $" [{Count}x]" : "";
                string toolStr = string.IsNullOrEmpty(ToolName) || ToolName == "Nenhuma" ? "" : $" [{ToolName}]";
                return $" As [{timeStr}] o jogador [{PlayerName}] estava em [{LocationName}] e {countStr} {BaseMessage}{toolStr}";
            }
        }

        private List<ActionLog> dailyLogs = new List<ActionLog>();
        private uint totalMoneyEarnedAtStartOfDay = 0;

        private string? lastDialogueText = null;

        private bool wasUsingTool = false;
        private bool wasInEvent = false;
        private bool wasEating = false;

        private Dictionary<string, int> npcGifts = new Dictionary<string, int>();
        private int completedBundlesCount = 0;

        public override void Entry(IModHelper helper)
        {
            this.Config = this.Helper.ReadConfig<ModConfig>();

            helper.Events.GameLoop.GameLaunched += OnGameLaunched;
            helper.Events.GameLoop.DayStarted += OnDayStarted;
            helper.Events.GameLoop.DayEnding += OnDayEnding;
            helper.Events.GameLoop.UpdateTicked += OnUpdateTicked;
            helper.Events.GameLoop.TimeChanged += OnTimeChanged;
            helper.Events.Player.InventoryChanged += OnInventoryChanged;
            helper.Events.Player.Warped += OnWarped;
            helper.Events.World.ObjectListChanged += OnObjectListChanged;
            helper.Events.World.TerrainFeatureListChanged += OnTerrainFeatureListChanged;
            helper.Events.Input.ButtonPressed += OnButtonPressed;
            helper.Events.World.NpcListChanged += OnNpcListChanged;
            helper.Events.Display.MenuChanged += OnMenuChanged;
            helper.Events.Multiplayer.PeerConnected += OnPeerConnected;
        }

        private void OnPeerConnected(object? sender, PeerConnectedEventArgs e)
        {
            var farmer = Game1.GetPlayer(e.Peer.PlayerID, true);
            string playerName = farmer?.Name ?? "Um jogador";
            LogAction($"{playerName} se juntou à fazenda", false);
        }

        private void OnGameLaunched(object? sender, GameLaunchedEventArgs e)
        {
            var configMenu = this.Helper.ModRegistry.GetApi<IGenericModConfigMenuApi>("spacechase0.GenericModConfigMenu");
            if (configMenu is null)
                return;

            configMenu.Register(
                mod: this.ModManifest,
                reset: () => this.Config = new ModConfig(),
                save: () => this.Helper.WriteConfig(this.Config)
            );

            configMenu.AddTextOption(
                mod: this.ModManifest,
                name: () => "Narração:",
                tooltip: () => "Escolha quando o narrador vai falar sobre as suas ações.",
                getValue: () => this.Config.NarrationMode,
                setValue: value => this.Config.NarrationMode = value,
                allowedValues: new string[] { "Diaria", "Por Turno", "A cada 3h", "A cada hora" }
            );

            configMenu.AddTextOption(
                mod: this.ModManifest,
                name: () => "OpenAI URL (Opcional)",
                tooltip: () => "Deixe em branco para usar o padrão da backend.",
                getValue: () => this.Config.OpenAiUrl,
                setValue: value => this.Config.OpenAiUrl = value
            );

            configMenu.AddTextOption(
                mod: this.ModManifest,
                name: () => "OpenAI API Key (Opcional)",
                tooltip: () => "Deixe em branco para usar a chave da backend.",
                getValue: () => this.Config.OpenAiApiKey,
                setValue: value => this.Config.OpenAiApiKey = value
            );

            configMenu.AddTextOption(
                mod: this.ModManifest,
                name: () => "OpenAI Model (Opcional)",
                tooltip: () => "Ex: gpt-3.5-turbo. Deixe em branco para usar o padrão.",
                getValue: () => this.Config.OpenAiModel,
                setValue: value => this.Config.OpenAiModel = value
            );

            configMenu.AddBoolOption(
                mod: this.ModManifest,
                name: () => "Usar Gemini para narrar",
                tooltip: () => "Se ativado, o backend tenta usar o Gemini quando houver chave configurada.",
                getValue: () => this.Config.UseGemini,
                setValue: value => this.Config.UseGemini = value
            );

            configMenu.AddTextOption(
                mod: this.ModManifest,
                name: () => "Gemini API Key (Opcional)",
                tooltip: () => "Se preenchido e a opção de uso estiver ativa, o backend prioriza o Gemini.",
                getValue: () => this.Config.GeminiApiKey,
                setValue: value => this.Config.GeminiApiKey = value
            );

            configMenu.AddTextOption(
                mod: this.ModManifest,
                name: () => "Gemini Model (Opcional)",
                tooltip: () => "Ex: gemini-2.0-flash. Deixe em branco para usar o padrão.",
                getValue: () => this.Config.GeminiModel,
                setValue: value => this.Config.GeminiModel = value
            );

            configMenu.AddTextOption(
                mod: this.ModManifest,
                name: () => "Gemini API Base (Opcional)",
                tooltip: () => "Deixe em branco para usar o padrão da backend.",
                getValue: () => this.Config.GeminiApiBase,
                setValue: value => this.Config.GeminiApiBase = value
            );

            configMenu.AddTextOption(
                mod: this.ModManifest,
                name: () => "ElevenLabs API Key (Opcional)",
                tooltip: () => "Deixe em branco para usar o TTS local da backend.",
                getValue: () => this.Config.ElevenLabsApiKey,
                setValue: value => this.Config.ElevenLabsApiKey = value
            );

            configMenu.AddTextOption(
                mod: this.ModManifest,
                name: () => "ElevenLabs Voice ID (Opcional)",
                tooltip: () => "ID da voz no ElevenLabs.",
                getValue: () => this.Config.ElevenLabsVoiceId,
                setValue: value => this.Config.ElevenLabsVoiceId = value
            );
        }

        private void OnMenuChanged(object? sender, MenuChangedEventArgs e)
        {
            if (e.NewMenu is Billboard)
            {
                LogAction("Interagiu com o quadro de missões ou calendário", false);
            }
            else if (e.NewMenu is LetterViewerMenu)
            {
                LogAction("Leu uma carta", false);
            }
            else if (e.NewMenu is JunimoNoteMenu)
            {
                LogAction("Consultou a nota dos Junimos no Centro Comunitário", false);
            }
        }

        private void OnTimeChanged(object? sender, TimeChangedEventArgs e)
        {
            if (this.Config.NarrationMode == "Por Turno")
            {
                if (e.NewTime == 1200 || e.NewTime == 1800)
                {
                    SendTurnLogsAndClear();
                }
            }
            else if (this.Config.NarrationMode == "A cada 3h")
            {
                if (e.NewTime == 900 || e.NewTime == 1200 || e.NewTime == 1500 || e.NewTime == 1800 || e.NewTime == 2100)
                {
                    SendTurnLogsAndClear();
                }
            }
            else if (this.Config.NarrationMode == "A cada hora")
            {
                if (e.NewTime % 100 == 0)
                {
                    SendTurnLogsAndClear();
                }
            }
        }

        private static string GetLocationName(GameLocation location, string fallbackName = null)
        {
            string locName = location?.Name ?? fallbackName ?? "Desconhecido";
            switch (locName)
            {
                case "Farm": return $"Fazenda {Game1.player?.farmName.Value ?? ""}".Trim();
                case "Town": return "Vila Pelicanos";
                case "Saloon": return "Saloon Fruta Estrelar";
                case "SeedShop": return "Armazém do Pierre";
                case "Blacksmith": return "Ferreiro";
                case "AnimalShop": return "Rancho da Marnie";
                case "JojaMart": return "Mercado Joja";
                case "Hospital": return "Clínica do Harvey";
                case "ScienceHouse": return "Carpintaria";
                case "Mountain": return "Montanha";
                case "Forest": return "Floresta Cinzaseiva";
                case "Beach": return "Praia";
                case "Mine": return "Minas";
                case "Desert": return "Deserto Calico";
                case "Woods": return "Bosque Secreto";
                case "Sewer": return "Esgotos";
                case "BugLand": return "Covil dos Insetos Mutantes";
                case "WitchSwamp": return "Pântano da Bruxa";
                case "WitchHut": return "Cabana da Bruxa";
                case "Greenhouse": return "Estufa";
                case "FarmCave": return "Caverna da Fazenda";
                case "CommunityCenter": return "Centro Comunitário";
                case "ArchaeologyHouse": return "Museu e Biblioteca";
                case "FarmHouse": return "Casa da Fazenda";
                case "Cellar": return "Porão";
                case "Club": return "Cassino";
                case "SandyHouse": return "Oásis";
                case "Trailer": return "Trailer da Penny";
                case "Tent": return "Tenda do Linus";
                case "ElliottHouse": return "Cabana do Elliott";
                case "JoshHouse": return "Casa do Alex";
                case "HaleyHouse": return "Casa da Haley";
                case "SamHouse": return "Casa do Sam";
                case "LeahHouse": return "Cabana da Leah";
                case "SebastianRoom": return "Quarto do Sebastian";
                case "HarveyRoom": return "Quarto do Harvey";
                case "IslandSouth": return "Ilha Gengibre (Sul)";
                case "IslandEast": return "Ilha Gengibre (Leste)";
                case "IslandNorth": return "Ilha Gengibre (Norte)";
                case "IslandWest": return "Ilha Gengibre (Oeste)";
                case "IslandHut": return "Cabana do Leo";
                case "VolcanoDungeon0": return "Vulcão";
                default:
                    if (locName.StartsWith("UndergroundMine")) return "Minas";
                    if (locName.StartsWith("BathHouse")) return "Casa de Banho";
                    if (locName.StartsWith("Cabin")) return "Cabana";
                    return locName;
            }
        }

        private void OnButtonPressed(object? sender, ButtonPressedEventArgs e)
        {
            if (!Context.IsWorldReady || Game1.player == null) return;

            if (e.Button.IsActionButton())
            {
                Microsoft.Xna.Framework.Vector2 tile = e.Cursor.GrabTile;
                var location = Game1.currentLocation;

                if (location != null)
                {
                    if (location.objects.TryGetValue(tile, out var obj))
                    {
                        if (obj.Name.Contains("TV")) LogAction("Assistiu TV", false);
                        else if (obj.Name.Contains("Sign")) LogAction("Leu uma placa", false);
                        else if (obj.Name.Contains("Fireplace")) LogAction("Interagiu com a lareira", false);
                        else if (obj.Name.Contains("Trash") || obj.Name.Contains("Garbage")) LogAction("Mexeu no lixo", false);
                    }

                    foreach (var furniture in location.furniture)
                    {
                        if (furniture.TileLocation == tile || furniture.GetBoundingBox().Contains((int)e.Cursor.AbsolutePixels.X, (int)e.Cursor.AbsolutePixels.Y))
                        {
                            if (furniture.Name.Contains("TV")) LogAction("Assistiu TV", false);
                            else if (furniture.Name.Contains("Fireplace")) LogAction("Interagiu com a lareira", false);
                        }
                    }

                    string action = location.doesTileHaveProperty((int)tile.X, (int)tile.Y, "Action", "Buildings");
                    if (action != null)
                    {
                        if (action.Contains("Garbage")) LogAction("Mexeu no lixo", false);
                    }
                }
            }
        }

        private int TimeToMinutes(int time)
        {
            return (time / 100) * 60 + (time % 100);
        }

        private int GetHalfHourChunk(int time)
        {
            int hour = time / 100;
            int minutes = time % 100;
            if (minutes >= 30) return hour * 100 + 30;
            return hour * 100;
        }

        private void OnUpdateTicked(object? sender, UpdateTickedEventArgs e)
        {
            if (!Context.IsWorldReady || Game1.player == null) return;

            foreach (var npc in Game1.player.friendshipData.Keys)
            {
                int currentGifts = Game1.player.friendshipData[npc].GiftsToday;
                if (npcGifts.TryGetValue(npc, out int previousGifts))
                {
                    if (currentGifts > previousGifts)
                    {
                        LogAction($"Deu um presente para {npc}", false);
                    }
                }
                npcGifts[npc] = currentGifts;
            }

            if (Game1.getLocationFromName("CommunityCenter") as CommunityCenter is { } currentCc)
            {
                int currentCompletedBundles = currentCc.bundles.Values.Count(v => v.All(x => x));
                if (currentCompletedBundles > completedBundlesCount)
                {
                    int diff = currentCompletedBundles - completedBundlesCount;
                    for (int i = 0; i < diff; i++)
                    {
                        LogAction("Completou um conjunto no Centro Comunitário", false);
                    }
                    completedBundlesCount = currentCompletedBundles;
                }
            }

            bool isInEvent = Game1.CurrentEvent != null;
            if (isInEvent && !wasInEvent)
            {
                LogAction($"Assistiu a uma cutscene", false);
            }
            wasInEvent = isInEvent;

            bool isEating = Game1.player.isEating;
            if (isEating && !wasEating)
            {
                var item = Game1.player.itemToEat;
                if (item != null)
                {
                    LogAction($"Consumiu {item.DisplayName}", false);
                }
            }
            wasEating = isEating;

            bool isUsingTool = Game1.player.UsingTool;
            
            if (isUsingTool && !wasUsingTool)
            {
                var tool = Game1.player.CurrentTool;
                if (tool != null)
                {
                    if (tool is StardewValley.Tools.WateringCan)
                    {
                        string cropWatered = "Solo";
                        var tileLocation = Game1.player.GetToolLocation() / 64f;
                        var tileVec = new Microsoft.Xna.Framework.Vector2((int)tileLocation.X, (int)tileLocation.Y);
                        
                        if (Game1.currentLocation.terrainFeatures.TryGetValue(tileVec, out var feature) && feature is HoeDirt dirt)
                        {
                            if (dirt.crop != null && dirt.crop.indexOfHarvest.Value > 0)
                            {
                                cropWatered = new StardewValley.Object(dirt.crop.indexOfHarvest.Value, 1).DisplayName;
                            }
                        }

                        LogAction($"Regou {cropWatered}", true);
                    }
                    else if (tool is StardewValley.Tools.MeleeWeapon weapon && weapon.isScythe())
                    {
                        LogAction($"Usou a foice", true);
                    }
                    else if (tool is StardewValley.Tools.Hoe)
                    {
                        LogAction($"Arou o solo", true);
                    }
                    else if (tool is StardewValley.Tools.FishingRod)
                    {
                        LogAction($"Começou a pescar usando", true);
                    }
                }
            }
            
            wasUsingTool = isUsingTool;

            if (Game1.activeClickableMenu is DialogueBox dialogueBox)
            {
                string text = "";
                try
                {
                    text = dialogueBox.getCurrentString();
                }
                catch { }

                if (!string.IsNullOrEmpty(text) && text != lastDialogueText)
                {
                    var speaker = Game1.currentSpeaker?.Name;
                    if (speaker != null)
                    {
                        LogAction($"Conversou com {speaker}, que disse: \"{text}\"", false);
                    }
                    else
                    {
                        LogAction($"Leu: \"{text}\"", false);
                    }
                    lastDialogueText = text;
                }
            }
            else if (Game1.activeClickableMenu == null)
            {
                lastDialogueText = null;
            }
        }

        private void LogAction(string message, bool includeTool = true, int amount = 1)
        {
            if (Game1.player == null) return;
            
            string toolName = includeTool ? (Game1.player.CurrentTool?.DisplayName ?? "Nenhuma") : "";
            int currentChunk = GetHalfHourChunk(Game1.timeOfDay);
            
            var existingLog = dailyLogs.FindLast(l => 
                l.BaseMessage == message && 
                l.ToolName == toolName && 
                l.InGameTime == currentChunk);

            if (existingLog != null)
            {
                existingLog.Count += amount;
                Monitor.Log($"Ação agrupada: {existingLog.GetFormattedString()}", LogLevel.Info);
                return;
            }

            var newLog = new ActionLog(message, toolName, currentChunk);
            newLog.Count = amount;
            dailyLogs.Add(newLog);
            Monitor.Log($"Ação registrada: {newLog.GetFormattedString()}", LogLevel.Info);
        }

        private int? GetPlayerUniqueId()
        {
            if (Game1.player == null) return null;

            var property = Game1.player.GetType().GetProperty("UniqueMultiplayerID");
            if (property != null)
            {
                var value = property.GetValue(Game1.player);
                if (value is int intValue)
                    return intValue;
                if (value is long longValue)
                    return (int)longValue;
                if (value is uint uintValue)
                    return (int)uintValue;
            }

            return null;
        }

        private void OnDayStarted(object? sender, DayStartedEventArgs e)
        {
            dailyLogs.Clear();
            totalMoneyEarnedAtStartOfDay = Game1.player.totalMoneyEarned;

            npcGifts.Clear();
            foreach (var npc in Game1.player.friendshipData.Keys)
            {
                npcGifts[npc] = Game1.player.friendshipData[npc].GiftsToday;
            }

            if (Game1.getLocationFromName("CommunityCenter") as CommunityCenter is { } cc)
            {
                completedBundlesCount = cc.bundles.Values.Count(v => v.All(x => x));
            }
        }

        private string GetQualityString(int quality)
        {
            switch (quality)
            {
                case 1: return " (Prata)";
                case 2: return " (Ouro)";
                case 4: return " (Irídio)";
                default: return "";
            }
        }

        private void OnDayEnding(object? sender, DayEndingEventArgs e)
        {
            uint earnedToday = Game1.player.totalMoneyEarned - totalMoneyEarnedAtStartOfDay;
            int shippingValue = 0;
            
            var shippingBin = Game1.getFarm().getShippingBin(Game1.player);
            var shippedItems = new Dictionary<string, (int amount, int value)>();

            foreach (var item in shippingBin)
            {
                if (item is StardewValley.Object obj)
                {
                    int itemValue = obj.sellToStorePrice() * obj.Stack;
                    shippingValue += itemValue;
                    
                    string qualityStr = GetQualityString(obj.Quality);
                    string key = $"{obj.DisplayName}{qualityStr}";
                    
                    if (shippedItems.ContainsKey(key))
                    {
                        var current = shippedItems[key];
                        shippedItems[key] = (current.amount + obj.Stack, current.value + itemValue);
                    }
                    else
                    {
                        shippedItems[key] = (obj.Stack, itemValue);
                    }
                }
            }

            foreach (var kvp in shippedItems)
            {
                LogAction($"Enviou {kvp.Key} ao mercado e vendeu por (Lucro: {kvp.Value.value} ouros)", false, kvp.Value.amount);
            }

            int totalEarned = (int)earnedToday + shippingValue;

            LogAction($"Faturou {totalEarned} ouros no final do dia", false);
            LogAction($"Foi dormir no final do dia {SDate.Now().ToLocaleString()}", false);

            SendTurnLogsAndClear();
        }

        private void SendTurnLogsAndClear()
        {
            if (dailyLogs.Count == 0) return;

            WriteLogToFile();
            
            var actionStrings = dailyLogs.Select(l => l.GetFormattedString()).ToList();
            bool isTurn = this.Config.NarrationMode == "Por Turno" || this.Config.NarrationMode == "A cada 3h" || this.Config.NarrationMode == "A cada hora";
            Task.Run(() => SendLogsToBackend(actionStrings, isTurn));
            
            dailyLogs.Clear();
            Monitor.Log("Histórico de ações limpo para o próximo turno/dia.", LogLevel.Info);
        }

        private static readonly HttpClient httpClient = new HttpClient();

        private void WriteLogToFile()
        {
            string path = Path.Combine(this.Helper.DirectoryPath, "acoes.txt");
            try
            {
                File.AppendAllLines(path, dailyLogs.Select(l => l.GetFormattedString()));
                Monitor.Log($"Salvo {dailyLogs.Count} ações em {path}", LogLevel.Info);
            }
            catch (Exception ex)
            {
                Monitor.Log($"Falha ao salvar em {path}: {ex.Message}", LogLevel.Error);
                string fallbackPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "acoes.txt");
                File.AppendAllLines(fallbackPath, dailyLogs.Select(l => l.GetFormattedString()));
                Monitor.Log($"Salvo na pasta alternativa: {fallbackPath}", LogLevel.Info);
            }
        }

        private async Task SendLogsToBackend(List<string> actionStrings, bool isTurn = false)
        {
            try
            {
                var payload = new {
                    actions = actionStrings,
                    player_name = Game1.player?.Name,
                    player_unique_id = GetPlayerUniqueId(),
                    is_multiplayer = Context.IsMultiplayer,
                    openai_url = this.Config.OpenAiUrl,
                    openai_api_key = this.Config.OpenAiApiKey,
                    openai_model = this.Config.OpenAiModel,
                    gemini_api_key = this.Config.GeminiApiKey,
                    gemini_model = this.Config.GeminiModel,
                    gemini_api_base = this.Config.GeminiApiBase,
                    use_gemini = this.Config.UseGemini,
                    eleven_labs_api_key = this.Config.ElevenLabsApiKey,
                    eleven_labs_voice_id = this.Config.ElevenLabsVoiceId
                };
                string jsonString = JsonSerializer.Serialize(payload);
                var content = new StringContent(jsonString, Encoding.UTF8, "application/json");
                
                string targetUrl = this.Config.BackendUrl;
                if (isTurn && targetUrl.EndsWith("/actions"))
                {
                    targetUrl = targetUrl.Substring(0, targetUrl.Length - 8) + "/actionsturn";
                }
                
                Monitor.Log($"Enviando ações para o backend ({targetUrl})...", LogLevel.Info);
                HttpResponseMessage response = await httpClient.PostAsync(targetUrl, content);
                
                if (response.IsSuccessStatusCode)
                {
                    Monitor.Log("Ações enviadas com sucesso para o backend.", LogLevel.Info);
                }
                else
                {
                    Monitor.Log($"Falha ao enviar ações. Status: {response.StatusCode}", LogLevel.Error);
                }
            }
            catch (Exception ex)
            {
                Monitor.Log($"Erro ao conectar com o backend: {ex.Message}", LogLevel.Error);
            }
        }

        private void OnWarped(object? sender, WarpedEventArgs e)
        {
            if (e.IsLocalPlayer)
            {
                string oldLoc = GetLocationName(e.OldLocation, e.OldLocation.Name);
                string newLoc = GetLocationName(e.NewLocation, e.NewLocation.Name);
                LogAction($"Foi para '{newLoc}'", false);

                if (e.NewLocation is MineShaft newShaft)
                {
                    if (newShaft.mineLevel > 120)
                    {
                        LogAction($"Chegou ao andar {newShaft.mineLevel - 120} da Caverna da Caveira", false);
                    }
                    else
                    {
                        LogAction($"Chegou ao andar {newShaft.mineLevel} das Minas", false);
                    }
                }
            }
        }

        private void OnNpcListChanged(object? sender, NpcListChangedEventArgs e)
        {
            if (e.Location != Game1.currentLocation) return;

            foreach (var npc in e.Removed)
            {
                if (npc is Monster monster && monster.Health <= 0)
                {
                    LogAction($"Derrotou um monstro: {monster.Name}", false);
                }
            }
        }

        private void OnInventoryChanged(object? sender, InventoryChangedEventArgs e)
        {
            if (!e.IsLocalPlayer) return;

            bool isCrafting = false;
            if (Game1.activeClickableMenu is CraftingPage)
            {
                isCrafting = true;
            }
            else if (Game1.activeClickableMenu is GameMenu gameMenu && gameMenu.currentTab == GameMenu.craftingTab)
            {
                isCrafting = true;
            }

            bool isJunimoNote = Game1.activeClickableMenu is JunimoNoteMenu;

            foreach (var item in e.Added)
            {
                string qualityStr = item is StardewValley.Object obj ? GetQualityString(obj.Quality) : "";
                if (isCrafting)
                {
                    LogAction($"Craftou {item.DisplayName}{qualityStr}", false, item.Stack);
                }
                else if (!isJunimoNote && Game1.activeClickableMenu == null && item.Category != StardewValley.Object.CraftingCategory && item.Category != StardewValley.Object.furnitureCategory && item.Category != StardewValley.Object.BigCraftableCategory)
                {
                    LogAction($"Colheu {item.DisplayName}{qualityStr}", false, item.Stack);
                }
                else
                {
                    LogAction($"Coletou {item.DisplayName}{qualityStr}", false, item.Stack);
                }
            }

            foreach (var change in e.QuantityChanged)
            {
                int amount = change.NewSize - change.OldSize;
                string qualityStr = change.Item is StardewValley.Object obj ? GetQualityString(obj.Quality) : "";
                if (amount > 0)
                {
                    if (isCrafting)
                        LogAction($"Craftou {change.Item.DisplayName}{qualityStr}", false, amount);
                    else if (!isJunimoNote && Game1.activeClickableMenu == null && change.Item.Category != StardewValley.Object.CraftingCategory && change.Item.Category != StardewValley.Object.furnitureCategory && change.Item.Category != StardewValley.Object.BigCraftableCategory)
                        LogAction($"Colheu {change.Item.DisplayName}{qualityStr}", false, amount);
                    else
                        LogAction($"Coletou {change.Item.DisplayName}{qualityStr}", false, amount);
                }
                else if (amount < 0)
                {
                    if (Game1.activeClickableMenu is ShopMenu)
                    {
                        LogAction($"Vendeu {change.Item.DisplayName}{qualityStr}", false, -amount);
                    }
                    else if (isJunimoNote)
                    {
                        LogAction($"Entregou {change.Item.DisplayName}{qualityStr} ao Centro Comunitário", false, -amount);
                    }
                    else if (Game1.activeClickableMenu == null)
                    {
                        if (change.Item.Category == StardewValley.Object.SeedsCategory || change.Item.Category == -74)
                        {
                            LogAction($"Plantou {change.Item.DisplayName}", false, -amount);
                        }
                        else if (change.Item.Category == StardewValley.Object.CraftingCategory || 
                                 change.Item.Category == StardewValley.Object.furnitureCategory ||
                                 change.Item.Category == StardewValley.Object.BigCraftableCategory ||
                                 change.Item.Category == -8 || change.Item.Category == -9)
                        {
                            LogAction($"Colocou {change.Item.DisplayName} no chão", false, -amount);
                        }
                        else
                        {
                            LogAction($"Usou {change.Item.DisplayName}{qualityStr}", false, -amount);
                        }
                    }
                }
            }

            foreach (var item in e.Removed)
            {
                string qualityStr = item is StardewValley.Object obj ? GetQualityString(obj.Quality) : "";
                if (Game1.activeClickableMenu is ShopMenu)
                {
                    LogAction($"Vendeu {item.DisplayName}{qualityStr}", false, item.Stack);
                }
                else if (isJunimoNote)
                {
                    LogAction($"Entregou {item.DisplayName}{qualityStr} ao Centro Comunitário", false, item.Stack);
                }
                else if (Game1.activeClickableMenu == null)
                {
                    if (item.Category == StardewValley.Object.SeedsCategory || item.Category == -74)
                    {
                        LogAction($"Plantou {item.DisplayName}", false, item.Stack);
                    }
                    else if (item.Category == StardewValley.Object.CraftingCategory || 
                             item.Category == StardewValley.Object.furnitureCategory || 
                             item.Category == StardewValley.Object.BigCraftableCategory ||
                             item.Category == -8 || item.Category == -9)
                    {
                        LogAction($"Colocou {item.DisplayName} no chão", false, item.Stack);
                    }
                    else
                    {
                        LogAction($"Usou {item.DisplayName}{qualityStr}", false, item.Stack);
                    LogAction($"Quebrou {obj.DisplayName} com ");
                }
                else
                {
                    LogAction($"Removeu {obj.DisplayName}");
                }
            }
        }

        private void OnTerrainFeatureListChanged(object? sender, TerrainFeatureListChangedEventArgs e)
        {
            foreach (var pair in e.Removed)
            {
                if (pair.Value is Tree)
                {
                    LogAction("Cortou uma Árvore com ");
                }
                else if (pair.Value is FruitTree)
                {
                    LogAction("Cortou uma Árvore Frutífera com");
                }
            }
        }
    }
}