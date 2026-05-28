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

namespace ActionLogger
{
    public class ModEntry : Mod
    {
        private class ActionLog
        {
            public string BaseMessage { get; set; }
            public string ToolName { get; set; }
            public int InGameTime { get; set; }
            public int Count { get; set; }
            public string PlayerName { get; set; }
            public string LocationName { get; set; }

            public ActionLog(string baseMessage, string toolName)
            {
                BaseMessage = baseMessage;
                ToolName = toolName;
                InGameTime = Game1.timeOfDay;
                PlayerName = Game1.player?.Name ?? "Nenhum";
                LocationName = Game1.currentLocation?.Name ?? "Desconhecido";
                Count = 1;
            }

            public string GetFormattedString()
            {
                string timeStr = Game1.getTimeOfDayString(InGameTime);
                string countStr = Count > 1 ? $" [{Count}x]" : "";
                string toolStr = string.IsNullOrEmpty(ToolName) ? "" : $" [Ferramenta: {ToolName}]";
                return $"[{timeStr}] [{PlayerName}] [Local: {LocationName}]{countStr} {BaseMessage}{toolStr}";
            }
        }

        private List<ActionLog> dailyLogs = new List<ActionLog>();
        private int moneyAtStartOfDay = 0;
        private string lastTalkedNPC = null;

        private bool wasUsingTool = false;
        private bool wasInEvent = false;

        public override void Entry(IModHelper helper)
        {
            helper.Events.GameLoop.DayStarted += OnDayStarted;
            helper.Events.GameLoop.DayEnding += OnDayEnding;
            helper.Events.GameLoop.UpdateTicked += OnUpdateTicked;
            helper.Events.Player.InventoryChanged += OnInventoryChanged;
            helper.Events.Player.Warped += OnWarped;
            helper.Events.World.ObjectListChanged += OnObjectListChanged;
            helper.Events.World.TerrainFeatureListChanged += OnTerrainFeatureListChanged;
            helper.Events.Display.MenuChanged += OnMenuChanged;
            helper.Events.Input.ButtonPressed += OnButtonPressed;
        }

        private void OnButtonPressed(object sender, ButtonPressedEventArgs e)
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

            bool isInEvent = Game1.CurrentEvent != null;
            if (isInEvent && !wasInEvent)
            {
                LogAction($"Assistiu a uma cutscene", false);
            }
            wasInEvent = isInEvent;

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
                            if (dirt.crop != null && !string.IsNullOrEmpty(dirt.crop.indexOfHarvest.Value))
                            {
                                cropWatered = ItemRegistry.Create(dirt.crop.indexOfHarvest.Value, 1).DisplayName;
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
                        LogAction($"Começou a pescar", true);
                    }
                }
            }
            
            wasUsingTool = isUsingTool;
        }

        private void LogAction(string message, bool includeTool = true)
        {
            if (Game1.player == null) return;
            
            string toolName = includeTool ? (Game1.player.CurrentTool?.Name ?? "Nenhuma") : "";
            
            if (dailyLogs.Count > 0)
            {
                var lastLog = dailyLogs[dailyLogs.Count - 1];
                // Agrupar se a mensagem e ferramenta forem as mesmas, e ocorreu nos últimos 20 minutos de jogo
                if (lastLog.BaseMessage == message && 
                    lastLog.ToolName == toolName && 
                    Math.Abs(TimeToMinutes(Game1.timeOfDay) - TimeToMinutes(lastLog.InGameTime)) <= 20)
                {
                    lastLog.Count++;
                    lastLog.InGameTime = Game1.timeOfDay;
                    Monitor.Log($"Ação agrupada: {lastLog.GetFormattedString()}", LogLevel.Info);
                    return;
                }
            }

            var newLog = new ActionLog(message, toolName);
            dailyLogs.Add(newLog);
            Monitor.Log($"Ação registrada: {newLog.GetFormattedString()}", LogLevel.Info);
        }

        private void OnDayStarted(object sender, DayStartedEventArgs e)
        {
            dailyLogs.Clear();
            moneyAtStartOfDay = Game1.player.Money;
            lastTalkedNPC = null;
        }

        private void OnDayEnding(object sender, DayEndingEventArgs e)
        {
            int earnedToday = Game1.player.Money - moneyAtStartOfDay;
            int shippingValue = 0;
            
            var shippingBin = Game1.getFarm().getShippingBin(Game1.player);
            foreach (var item in shippingBin)
            {
                if (item is StardewValley.Object obj)
                {
                    shippingValue += obj.sellToStorePrice() * obj.Stack;
                }
            }

            int totalEarned = Math.Max(0, earnedToday + shippingValue);

            LogAction($"faturou {totalEarned} no final do dia", false);
            LogAction($"Foi dormir no final do dia {SDate.Now().ToLocaleString()}", false);

            WriteLogToFile();
            
            var actionStrings = dailyLogs.Select(l => l.GetFormattedString()).ToList();
            Task.Run(() => SendLogsToBackend(actionStrings));
            
            dailyLogs.Clear();
            Monitor.Log("Histórico de ações limpo para o próximo dia.", LogLevel.Info);
        }

        private static readonly HttpClient httpClient = new HttpClient();

        private void WriteLogToFile()
        {
            string path = @"C:\ações.txt";
            try
            {
                File.AppendAllLines(path, dailyLogs.Select(l => l.GetFormattedString()));
                Monitor.Log($"Salvo {dailyLogs.Count} ações em {path}", LogLevel.Info);
            }
            catch (Exception ex)
            {
                Monitor.Log($"Falha ao salvar em {path}: {ex.Message}", LogLevel.Error);
                string fallbackPath = Path.Combine(Helper.DirectoryPath, "ações.txt");
                File.AppendAllLines(fallbackPath, dailyLogs.Select(l => l.GetFormattedString()));
                Monitor.Log($"Salvo na pasta alternativa: {fallbackPath}", LogLevel.Info);
            }
        }

        private async Task SendLogsToBackend(List<string> actionStrings)
        {
            try
            {
                var payload = new { actions = actionStrings };
                string jsonString = JsonSerializer.Serialize(payload);
                var content = new StringContent(jsonString, Encoding.UTF8, "application/json");
                
                Monitor.Log("Enviando ações para o backend...", LogLevel.Info);
                HttpResponseMessage response = await httpClient.PostAsync("http://localhost:8000/actions", content);
                
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

        private void OnWarped(object sender, WarpedEventArgs e)
        {
            if (e.IsLocalPlayer)
            {
                LogAction($"Saiu de '{e.OldLocation.Name}' para '{e.NewLocation.Name}'", false);
            }
        }

        private void OnInventoryChanged(object sender, InventoryChangedEventArgs e)
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

            foreach (var item in e.Added)
            {
                if (isCrafting)
                    LogAction($"Craftou {item.Stack}x {item.Name}", false);
                else
                    LogAction($"Coletou {item.Stack}x {item.Name}", false);
            }

            foreach (var change in e.QuantityChanged)
            {
                int amount = change.NewSize - change.OldSize;
                if (amount > 0)
                {
                    if (isCrafting)
                        LogAction($"Craftou {amount}x {change.Item.Name}", false);
                    else
                        LogAction($"Coletou {amount}x {change.Item.Name}", false);
                }
                else if (amount < 0 && Game1.activeClickableMenu is ShopMenu)
                {
                    LogAction($"Vendeu {-amount}x {change.Item.Name}", false);
                }
            }

            if (Game1.activeClickableMenu is ShopMenu)
            {
                foreach (var item in e.Removed)
                {
                    LogAction($"Vendeu {item.Stack}x {item.Name}", false);
                }
            }
        }

        private void OnObjectListChanged(object sender, ObjectListChangedEventArgs e)
        {
            foreach (var pair in e.Removed)
            {
                var obj = pair.Value;
                if (obj.Name.Contains("Stone") || obj.Name.Contains("Rock"))
                {
                    LogAction($"Quebrou {obj.Name}");
                }
                else if (obj.Name.Contains("Weed"))
                {
                    LogAction($"Cortou {obj.Name}");
                }
                else if (obj.Name.Contains("Twig") || obj.Name.Contains("Wood"))
                {
                    LogAction($"Quebrou {obj.Name}");
                }
            }
        }

        private void OnTerrainFeatureListChanged(object sender, TerrainFeatureListChangedEventArgs e)
        {
            foreach (var pair in e.Removed)
            {
                if (pair.Value is Tree)
                {
                    LogAction("Cortou Arvore");
                }
                else if (pair.Value is FruitTree)
                {
                    LogAction("Cortou Arvore Frutifera");
                }
            }
        }

        private void OnMenuChanged(object sender, MenuChangedEventArgs e)
        {
            if (e.NewMenu is DialogueBox dialogueBox)
            {
                var speaker = Game1.currentSpeaker?.Name;
                if (speaker != null)
                {
                    string text = "";
                    try
                    {
                        text = dialogueBox.getCurrentString();
                    }
                    catch { }

                    // Se mudou de NPC ou se há texto capturado novo, registra a ação.
                    if (speaker != lastTalkedNPC || !string.IsNullOrEmpty(text))
                    {
                        string msg = $"Conversou com {speaker}";
                        if (!string.IsNullOrEmpty(text))
                        {
                            msg += $": \"{text}\"";
                        }
                        LogAction(msg, false);
                        lastTalkedNPC = speaker;
                    }
                }
            }
            else if (e.NewMenu == null)
            {
                lastTalkedNPC = null;
            }
        }
    }
}