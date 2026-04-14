import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def draw_diagram():
    fig, ax = plt.subplots(figsize=(14, 18), facecolor='#FAFAFA')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Colors
    c_user = '#3B82F6'    # Blue
    c_agent = '#8B5CF6'   # Indigo
    c_tool = '#10B981'    # Green
    c_mem = '#F59E0B'     # Yellow
    c_text = '#1F2937'    # Dark Gray
    c_bg = '#FAFAFA'

    # Helper function for boxes
    def add_box(x, y, w, h, text, color, text_color='white', font_size=12, style='normal'):
        box = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2",
                                      fc=color, ec="none", alpha=0.9)
        ax.add_patch(box)
        ax.text(x + w/2, y + h/2, text, ha='center', va='center',
                color=text_color, fontsize=font_size, fontweight='bold',
                fontfamily='sans-serif', fontstyle=style)

    # Helper function for arrows
    def add_arrow(x1, y1, x2, y2, color='#9CA3AF', rad=0.0):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=color, lw=2,
                                    connectionstyle=f"arc3,rad={rad}"))

    # Title
    ax.text(50, 95, "H E R M E S   A G E N T   E X E C U T I O N   F L O W", ha='center', va='center',
            fontsize=24, fontweight='900', color=c_text)

    # 1. User Input Layer
    add_box(10, 85, 30, 6, "User Input (CLI)", c_user)
    add_box(60, 85, 30, 6, "User Input (Gateway)", c_user)
    
    # 2. Agent Initialization
    add_box(30, 72, 40, 8, "AIAgent Initialization\n(Load Tools, Setup Memory)", c_agent)
    add_arrow(25, 85, 40, 80)
    add_arrow(75, 85, 60, 80)

    # 3. Agent Loop Start
    add_box(35, 60, 30, 6, "Agent Loop: run_conversation()", c_agent)
    add_arrow(50, 72, 50, 66)

    # 4. Context & Memory
    add_box(10, 50, 25, 6, "Memory Manager\n(Prefetch)", c_mem)
    add_box(65, 50, 25, 6, "Prompt Builder\n(System Prompt)", c_mem)
    add_arrow(50, 60, 22.5, 56, rad=0.2)
    add_arrow(50, 60, 77.5, 56, rad=-0.2)
    add_arrow(22.5, 50, 45, 46, rad=0.2)
    add_arrow(77.5, 50, 55, 46, rad=-0.2)

    # 5. LLM Call
    add_box(35, 40, 30, 6, "LLM API Call\n(Streaming/Sync)", c_agent)
    add_arrow(50, 60, 50, 46)

    # 6. Decision Split
    add_box(35, 28, 30, 6, "Parse LLM Output", '#6B7280')
    add_arrow(50, 40, 50, 34)

    # 7. Tool Execution Branch
    add_box(15, 15, 25, 6, "Execute Tools\n(Terminal, Browser...)", c_tool)
    add_arrow(35, 28, 27.5, 21, rad=0.2)
    ax.text(28, 25, "tool_calls", color=c_tool, fontweight='bold', rotation=45)
    
    # Loop back from tools
    add_arrow(15, 18, 10, 45, rad=-0.5, color=c_tool)
    ax.text(8, 30, "Append Tool Results\nNext Iteration", rotation=90, color=c_tool, fontsize=10, fontweight='bold')

    # 8. Final Response Branch
    add_box(60, 15, 25, 6, "Final Response\n(Text to User)", c_user)
    add_arrow(65, 28, 72.5, 21, rad=-0.2)
    ax.text(70, 25, "text only", color=c_user, fontweight='bold', rotation=-45)

    # Context Compressor (Side note)
    add_box(80, 35, 15, 4, "Context\nCompressor", c_mem, font_size=9)
    add_arrow(65, 31, 80, 37, rad=0.1, color='#D1D5DB')
    
    # Interrupt mechanism
    add_box(85, 65, 12, 4, "Interrupt\nHandler", '#EF4444', font_size=9)
    add_arrow(85, 65, 65, 63, color='#EF4444', rad=-0.1)

    # Save
    plt.savefig('/workspace/hermes_flow.png', dpi=300, bbox_inches='tight', facecolor=c_bg)
    plt.close()

if __name__ == "__main__":
    draw_diagram()
