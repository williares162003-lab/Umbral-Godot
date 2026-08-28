extends Node3D

const HEIGHTMAP_PATH := "res://assets/terrain/heightmaps/umbral_world_heightmap.r16"
const HEIGHTMAP_RESOLUTION := 2048
const MAP_SIZE_METERS := 10000.0
const VERTEX_SPACING := MAP_SIZE_METERS / HEIGHTMAP_RESOLUTION
const TERRAIN_HEIGHT_METERS := 1350.0
const TERRAIN_BASE_HEIGHT := -180.0
const CAPTURE_PATH := "res://captures/terrain_world_10km.png"

var terrain: Terrain3D


func _ready() -> void:
	terrain = Terrain3D.new()
	terrain.name = "UmbralTerrain10km"
	add_child(terrain, true)

	terrain.region_size = 1024
	terrain.vertex_spacing = VERTEX_SPACING
	terrain.material.world_background = Terrain3DMaterial.NONE
	terrain.material.auto_shader = true
	terrain.material.set_shader_param("auto_base_texture", 0)
	terrain.material.set_shader_param("auto_overlay_texture", 1)
	terrain.material.set_shader_param("auto_slope", 0.45)
	terrain.material.set_shader_param("blend_sharpness", 0.45)
	terrain.assets = Terrain3DAssets.new()
	terrain.assets.set_texture(
		0,
		create_texture_asset("RockPreview", Color("59615f"), 0.075)
	)
	terrain.assets.set_texture(
		1,
		create_texture_asset("GrassPreview", Color("4c7046"), 0.12)
	)

	var height_image := Terrain3DUtil.load_image(
		HEIGHTMAP_PATH,
		ResourceLoader.CACHE_MODE_IGNORE,
		Vector2(0.0, 1.0),
		Vector2i(HEIGHTMAP_RESOLUTION, HEIGHTMAP_RESOLUTION)
	)
	if height_image.is_empty():
		push_error("No se pudo cargar el mapa de altura: %s" % HEIGHTMAP_PATH)
		return
	print(
		"Umbral heightmap: formato=%s rango=%s"
		% [height_image.get_format(), Terrain3DUtil.get_min_max(height_image)]
	)

	var maps: Array[Image]
	maps.resize(Terrain3DRegion.TYPE_MAX)
	maps[Terrain3DRegion.TYPE_HEIGHT] = height_image

	var origin := Vector3.ZERO
	terrain.data.import_images(
		maps,
		origin,
		TERRAIN_BASE_HEIGHT,
		TERRAIN_HEIGHT_METERS
	)
	print(
		"Umbral: mundo base cargado (%.0f x %.0f m, %.3f m por vertice)."
		% [MAP_SIZE_METERS, MAP_SIZE_METERS, VERTEX_SPACING]
	)

	if "--capture-terrain" in OS.get_cmdline_user_args():
		await capture_terrain_preview()


func capture_terrain_preview() -> void:
	for frame in 20:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw

	var capture_directory := ProjectSettings.globalize_path("res://captures")
	DirAccess.make_dir_recursive_absolute(capture_directory)
	var image := get_viewport().get_texture().get_image()
	var error := image.save_png(ProjectSettings.globalize_path(CAPTURE_PATH))
	if error == OK:
		print("Umbral: captura 10 km guardada en %s." % CAPTURE_PATH)
	else:
		push_error("No se pudo guardar la captura 3D: %s" % error_string(error))
	get_tree().quit()


func create_texture_asset(
	asset_name: String,
	albedo_color: Color,
	uv_scale: float
) -> Terrain3DTextureAsset:
	var albedo_image := Image.create(64, 64, false, Image.FORMAT_RGBA8)
	var packed_albedo := albedo_color
	packed_albedo.a = 0.5
	albedo_image.fill(packed_albedo)
	albedo_image.generate_mipmaps()

	var normal_image := Image.create(64, 64, false, Image.FORMAT_RGBA8)
	normal_image.fill(Color(0.5, 0.5, 1.0, 0.9))
	normal_image.generate_mipmaps()

	var texture_asset := Terrain3DTextureAsset.new()
	texture_asset.name = asset_name
	texture_asset.albedo_texture = ImageTexture.create_from_image(albedo_image)
	texture_asset.normal_texture = ImageTexture.create_from_image(normal_image)
	texture_asset.uv_scale = uv_scale
	texture_asset.detiling_rotation = 0.14
	return texture_asset
