"""
Static data for projects.
"""

PROJECTS = [
    {
        "id": 1,
        "name": "RendezViewz",
        "short_description": "A collaborative watch party platform that enhances social viewing experiences",
        "description": """
        <p>RendezViewz is a platform that transforms how people watch content together online. 
        It features real-time synchronization, chat, reactions, and interactive elements that make remote viewing feel more personal and engaging.</p>
        
        <p>The platform synchronizes video playback across all participants, ensuring everyone watches the same moment together. 
        Users can react in real-time, share comments, and even create custom reactions to express themselves during viewing sessions.</p>
        """,
        "image_url": "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/GalleryArt/website/rendezviewz.png",
        "timeline": "Jan 2023 - Present",
        "technologies": "React, Node.js, WebSocket, WebRTC",
        "demo_url": "https://rendezviewz.demo.com",
        "github_url": "https://github.com/charlottezhu/rendezviewz",
        "features": [
            "Real-time video synchronization",
            "Live chat and reactions",
            "Custom emoji support",
            "Session recording and playback",
            "Multi-platform support",
        ],
        "images": [
            {
                "url": "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/projects/rendezviewz-1.jpg",
                "caption": "Watch party interface",
            },
            {
                "url": "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/projects/rendezviewz-2.jpg",
                "caption": "Custom reactions panel",
            },
        ],
    },
    {
        "id": 2,
        "name": "Vera",
        "short_description": "An intelligent warning system for responsible LLM usage",
        "description": """
        <p>Vera is a warning system that helps developers and users understand the potential risks and biases in their LLM applications. 
        It provides real-time analysis and suggestions for more responsible AI usage.</p>
        
        <p>The system monitors LLM interactions and provides immediate feedback on potential ethical concerns, bias detection, 
        and suggestions for more inclusive and responsible AI usage patterns.</p>
        """,
        "image_url": "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/projects/vera-hero.jpg",
        "timeline": "Mar 2023 - Dec 2023",
        "technologies": "Python, PyTorch, FastAPI, React",
        "demo_url": "https://vera-demo.herokuapp.com",
        "github_url": "https://github.com/charlottezhu/vera",
        "features": [
            "Real-time bias detection",
            "Ethical AI guidelines",
            "Developer dashboard",
            "Integration APIs",
            "Customizable warning thresholds",
        ],
    },
    {
        "id": 3,
        "name": "Echo",
        "short_description": "A love simulation game exploring emotional intelligence",
        "description": """
        <p>LoveSims is an interactive narrative game that helps players develop emotional intelligence through simulated relationships 
        and conversations. It features adaptive storylines and realistic character development.</p>
        
        <p>The game uses advanced natural language processing to understand player responses and adapt the story accordingly. 
        Characters remember past interactions and develop relationships based on the player's emotional intelligence and communication style.</p>
        """,
        "image_url": "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/GalleryArt/website/Echo.png",
        "timeline": "Sep 2022 - Feb 2023",
        "technologies": "Unity, C#, DialogueFlow",
        "demo_url": "https://lovesims.itch.io/demo",
        "github_url": "https://github.com/charlottezhu/lovesims",
        "features": [
            "Adaptive storylines",
            "Character memory system",
            "Emotional intelligence scoring",
            "Multiple relationship paths",
            "Mini-games and activities",
        ],
    },
    {
        "id": 4,
        "name": "LoveSims",
        "short_description": "A love simulation game exploring emotional intelligence",
        "description": """
        <p>LoveSims is an interactive narrative game that helps players develop emotional intelligence through simulated relationships 
        and conversations. It features adaptive storylines and realistic character development.</p>
        
        <p>The game uses advanced natural language processing to understand player responses and adapt the story accordingly. 
        Characters remember past interactions and develop relationships based on the player's emotional intelligence and communication style.</p>
        """,
        "image_url": "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/projects/lovesims-hero.jpg",
        "timeline": "Sep 2022 - Feb 2023",
        "technologies": "Unity, C#, DialogueFlow",
        "demo_url": "https://lovesims.itch.io/demo",
        "github_url": "https://github.com/charlottezhu/lovesims",
        "features": [
            "Adaptive storylines",
            "Character memory system",
            "Emotional intelligence scoring",
            "Multiple relationship paths",
            "Mini-games and activities",
        ],
    },
    {
        "id": 5,
        "name": "Voyage",
        "short_description": "A love simulation game exploring emotional intelligence",
        "description": """
        <p>LoveSims is an interactive narrative game that helps players develop emotional intelligence through simulated relationships 
        and conversations. It features adaptive storylines and realistic character development.</p>
        
        <p>The game uses advanced natural language processing to understand player responses and adapt the story accordingly. 
        Characters remember past interactions and develop relationships based on the player's emotional intelligence and communication style.</p>
        """,
        "image_url": "https://dgcfnvaratrfzwofqohg.supabase.co/storage/v1/object/public/projects/lovesims-hero.jpg",
        "timeline": "Sep 2022 - Feb 2023",
        "technologies": "Unity, C#, DialogueFlow",
        "demo_url": "https://lovesims.itch.io/demo",
        "github_url": "https://github.com/charlottezhu/lovesims",
        "features": [
            "Adaptive storylines",
            "Character memory system",
            "Emotional intelligence scoring",
            "Multiple relationship paths",
            "Mini-games and activities",
        ],
    },
]


def get_all_projects():
    """Return all projects."""
    return PROJECTS


def get_project_by_id(project_id):
    """Return a specific project by ID."""
    for project in PROJECTS:
        if project["id"] == project_id:
            return project
    return None
